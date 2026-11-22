//! siesta against PyBall's committed plugin contract, `plugins/openapi.json`.
//!
//! For each call siesta makes, the response schema becomes sample JSON that siesta's own
//! types must decode, and every field they read must be in it. A renamed field, a changed
//! type or a field that became nullable fails here once the schema is regenerated.

use serde::Serialize;
use serde::de::DeserializeOwned;
use serde_json::{Map, Value, json};

use crate::api::{ACTIVE_MEETUP, EVENTS, Endpoint, LINEUP, LineupBody, check_endpoints};

const SCHEMA: &str = include_str!("../../openapi.json");

#[test]
fn every_call_siesta_makes_matches_the_schema() {
    let schema: Value = serde_json::from_str(SCHEMA).unwrap();
    check_endpoints(&schema);
}

#[test]
fn the_client_calls_pyball_only_through_its_endpoints() {
    // A path written anywhere but the endpoints! table would go unchecked.
    let source = include_str!("api.rs");
    let table = source.find("endpoints! {").unwrap();
    let rest = &source[source[table..].find("\n}\n").unwrap() + table..];
    assert!(
        !rest.contains("\"/"),
        "api.rs builds a PyBall path outside endpoints!: declare the call there"
    );
}

#[test]
fn the_lineup_body_matches_the_schema() {
    let schema: Value = serde_json::from_str(SCHEMA).unwrap();
    let body = serde_json::to_value(LineupBody {
        players: &["p1".to_string()],
        team_algorithm: "balanceado",
    })
    .unwrap();
    let request = &operation(&schema, &LINEUP)["requestBody"];
    let target = &request["content"]["application/json"]["schema"];
    assert!(
        accepts(&schema, target, &body),
        "PyBall no longer accepts {body} as a lineup body"
    );
}

#[test]
fn siesta_can_resume_the_event_stream() {
    let schema: Value = serde_json::from_str(SCHEMA).unwrap();
    let params = operation(&schema, &EVENTS)["parameters"]
        .as_array()
        .unwrap();
    assert!(
        params
            .iter()
            .any(|p| p["in"] == "header" && p["name"] == "last-event-id"),
        "GET /events no longer reads the Last-Event-ID header"
    );
}

#[test]
fn no_active_meetup_is_a_404() {
    let schema: Value = serde_json::from_str(SCHEMA).unwrap();
    let responses = &operation(&schema, &ACTIVE_MEETUP)["responses"];
    assert!(
        responses.get("404").is_some(),
        "GET /meetups/active no longer answers 404 when there is no active meetup"
    );
}

/// The answer to `endpoint`, sampled from its schema, decodes into `T`; and every field
/// `T` reads is in the sample.
pub fn check<T: DeserializeOwned + Serialize>(schema: &Value, endpoint: &Endpoint<T>) {
    let (method, path) = (endpoint.method, endpoint.path);
    let target = response(operation(schema, endpoint))
        .unwrap_or_else(|| panic!("{method} {path} has no success response schema"));
    for filled in [true, false] {
        let sample = sample(schema, target, filled);
        let decoded: T = serde_json::from_value(sample.clone())
            .unwrap_or_else(|e| panic!("{method} {path}: siesta cannot decode {sample}: {e}"));
        if filled {
            let read = serde_json::to_value(decoded).unwrap();
            assert_present(&read, &sample, &format!("{method} {path}"));
        }
    }
}

fn operation<'a, T>(schema: &'a Value, endpoint: &Endpoint<T>) -> &'a Value {
    let (method, path) = (endpoint.method, endpoint.path);
    let op = &schema["paths"][path][method.to_lowercase()];
    assert!(op.is_object(), "{method} {path} is not in the schema");
    op
}

/// The success response's schema: JSON, or the data of each server-sent event.
fn response(op: &Value) -> Option<&Value> {
    let (_, ok) = op["responses"]
        .as_object()?
        .iter()
        .find(|(code, _)| code.starts_with('2'))?;
    let content = &ok["content"];
    let json = &content["application/json"]["schema"];
    let sse = &content["text/event-stream"]["itemSchema"]["properties"]["data"]["contentSchema"];
    [json, sse].into_iter().find(|s| s.is_object())
}

/// A value matching `target`: with every field and nullable filled in, or with nullables
/// null and optional fields left out.
fn sample(schema: &Value, target: &Value, filled: bool) -> Value {
    let target = resolve(schema, target);
    if let Some(variants) = target["anyOf"].as_array() {
        let null = variants.iter().any(|v| v["type"] == "null");
        if null && !filled {
            return Value::Null;
        }
        let some = variants.iter().find(|v| v["type"] != "null").unwrap();
        return sample(schema, some, filled);
    }
    match target["type"].as_str() {
        Some("object") => {
            let required = target["required"].as_array().cloned().unwrap_or_default();
            let mut out = Map::new();
            for (name, field) in target["properties"].as_object().into_iter().flatten() {
                if filled || required.contains(&json!(name)) {
                    out.insert(name.clone(), sample(schema, field, filled));
                }
            }
            Value::Object(out)
        }
        Some("array") => json!([sample(schema, &target["items"], filled)]),
        Some("string") => json!("2026-11-25T20:00:00"),
        Some("integer") => json!(1),
        Some("number") => json!(1.5),
        Some("boolean") => json!(true),
        other => panic!("no sample for schema type {other:?}"),
    }
}

/// Whether `target` accepts `value`: known fields of the right type, required ones present.
fn accepts(schema: &Value, target: &Value, value: &Value) -> bool {
    let target = resolve(schema, target);
    if let Some(variants) = target["anyOf"].as_array() {
        return variants.iter().any(|v| accepts(schema, v, value));
    }
    match (target["type"].as_str(), value) {
        (Some("object"), Value::Object(fields)) => {
            let props = &target["properties"];
            let required = target["required"].as_array().cloned().unwrap_or_default();
            fields
                .iter()
                .all(|(k, v)| props.get(k).is_some_and(|p| accepts(schema, p, v)))
                && required
                    .iter()
                    .all(|r| fields.contains_key(r.as_str().unwrap()))
        }
        (Some("array"), Value::Array(items)) => {
            items.iter().all(|v| accepts(schema, &target["items"], v))
        }
        (Some("string"), Value::String(_)) | (Some("boolean"), Value::Bool(_)) => true,
        (Some("integer"), Value::Number(n)) => n.is_i64() || n.is_u64(),
        (Some("number"), Value::Number(_)) | (Some("null"), Value::Null) => true,
        _ => false,
    }
}

fn resolve<'a>(schema: &'a Value, target: &'a Value) -> &'a Value {
    match target["$ref"].as_str() {
        Some(r) => {
            let name = r.strip_prefix("#/components/schemas/").unwrap();
            resolve(schema, &schema["components"]["schemas"][name])
        }
        None => target,
    }
}

/// Every field siesta read back from `sample` is in it, at any depth.
fn assert_present(read: &Value, sample: &Value, at: &str) {
    match (read, sample) {
        (Value::Object(read), Value::Object(sample)) => {
            for (name, value) in read {
                let Some(given) = sample.get(name) else {
                    panic!("{at}: siesta reads `{name}`, which the schema does not have");
                };
                assert_present(value, given, &format!("{at}.{name}"));
            }
        }
        (Value::Array(read), Value::Array(sample)) => {
            for (value, given) in read.iter().zip(sample) {
                assert_present(value, given, at);
            }
        }
        _ => {}
    }
}
