//! A plugin's calls against PyBall's committed plugin contract, `plugins/openapi.json`.
//!
//! For each call a plugin makes, the response schema becomes sample JSON that the
//! plugin's own types must decode, and every field they read must be in it. A renamed
//! field, a changed type or a field that became nullable fails once the schema is
//! regenerated.

use serde::Serialize;
use serde::de::DeserializeOwned;
use serde_json::{Map, Value, json};

use crate::Endpoint;

/// A body a plugin sends, as the contract test sends it; `()` sends none.
pub trait Sample: Serialize + Sized {
    fn sample() -> Option<Self>;
}

impl Sample for () {
    fn sample() -> Option<Self> {
        None
    }
}

/// PyBall accepts the body the plugin sends to `endpoint`, or needs none if it sends none; the
/// answer, sampled from its schema, decodes into `T`; and every field `T` reads is in it.
pub fn check<In: Sample, T: DeserializeOwned + Serialize>(
    schema: &Value,
    endpoint: &Endpoint<In, T>,
) {
    let (method, path) = (endpoint.method, endpoint.path);
    let request = &operation(schema, endpoint)["requestBody"];
    match In::sample() {
        Some(body) => {
            let body = serde_json::to_value(body).unwrap();
            let target = &request["content"]["application/json"]["schema"];
            assert!(
                accepts(schema, target, &body),
                "{method} {path}: PyBall no longer accepts {body} as its body"
            );
        }
        None => assert!(
            request["required"] != json!(true),
            "{method} {path} now needs a body, which the plugin does not send"
        ),
    }
    let target = response(operation(schema, endpoint))
        .unwrap_or_else(|| panic!("{method} {path} has no success response schema"));
    for filled in [true, false] {
        let sample = sample(schema, target, filled);
        let decoded: T = serde_json::from_value(sample.clone())
            .unwrap_or_else(|e| panic!("{method} {path}: the plugin cannot decode {sample}: {e}"));
        if filled {
            let read = serde_json::to_value(decoded).unwrap();
            assert_present(&read, &sample, &format!("{method} {path}"));
        }
    }
}

pub fn operation<'a, In, T>(schema: &'a Value, endpoint: &Endpoint<In, T>) -> &'a Value {
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

/// Every field the plugin read back from `sample` is in it, at any depth.
fn assert_present(read: &Value, sample: &Value, at: &str) {
    match (read, sample) {
        (Value::Object(read), Value::Object(sample)) => {
            for (name, value) in read {
                let Some(given) = sample.get(name) else {
                    panic!("{at}: the plugin reads `{name}`, which the schema does not have");
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
