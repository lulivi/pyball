# Copyright (c) 2026 Luis Liñán
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

"""A plugin's calls against PyBall's committed plugin contract, ``plugins/openapi.json``.

For each call a plugin makes, the response schema becomes sample JSON that the plugin's
own types must decode, and every field they read must be in it. A renamed field, a
changed type or a field that became nullable fails once the schema is regenerated.
"""

from __future__ import annotations

from typing import Any, Iterable

from pyball_client.api import Endpoint

Schema = dict[str, Any]


def check_endpoints(schema: Schema, endpoints: Iterable[Endpoint[Any]]) -> None:
    """Check every endpoint a plugin declares; raise AssertionError on the first mismatch."""
    for endpoint in endpoints:
        check(schema, endpoint)


def check(schema: Schema, endpoint: Endpoint[Any]) -> None:
    """PyBall accepts what the plugin sends to ``endpoint`` and the plugin decodes its answer.

    The body (``endpoint.sample``) matches the request schema, or none is required; each
    query parameter exists; the answer, sampled from its schema with every field filled
    and with only the required ones, decodes into ``endpoint.out``; and every field the
    plugin reads is in it. A ``bytes`` answer only needs a non-JSON success response.
    """
    at = f"{endpoint.method} {endpoint.path}"
    op = operation(schema, endpoint)
    request = op.get("requestBody", {})
    if endpoint.sample is not None:
        body = endpoint.sample.model_dump(mode="json")
        target = request.get("content", {}).get("application/json", {}).get("schema", {})
        assert _accepts(schema, target, body), f"{at}: PyBall no longer accepts {body}"
    else:
        assert not request.get("required"), f"{at} now needs a body, which the plugin omits"
    known = {p["name"] for p in op.get("parameters", []) if p["in"] == "query"}
    for name in endpoint.query:
        assert name in known, f"{at} no longer takes the query parameter {name}"

    content = _success(op, at)
    if endpoint.out is bytes:
        assert any(t != "application/json" for t in content), f"{at} no longer answers bytes"
        return
    target = _response_schema(content, at)
    for filled in (True, False):
        sample = _sample(schema, target, filled)
        try:
            decoded = endpoint.adapter.validate_python(sample)
        except ValueError as exc:
            raise AssertionError(f"{at}: the plugin cannot decode {sample}: {exc}") from exc
        if filled:
            read = endpoint.adapter.dump_python(decoded, mode="json", by_alias=True)
            _assert_present(read, sample, at)


def operation(schema: Schema, endpoint: Endpoint[Any]) -> Schema:
    """Return the schema's operation for ``endpoint``; fail if it is gone."""
    op = schema["paths"].get(endpoint.path, {}).get(endpoint.method.lower())
    assert isinstance(op, dict), f"{endpoint.method} {endpoint.path} is not in the schema"
    return op


def _success(op: Schema, at: str) -> Schema:
    for code, response in op["responses"].items():
        if code.startswith("2"):
            content: Schema = response.get("content", {})
            return content
    raise AssertionError(f"{at} has no success response")


def _response_schema(content: Schema, at: str) -> Schema:
    """The JSON answer's schema, or the data of each server-sent event."""
    if "application/json" in content and content["application/json"].get("schema"):
        found: Schema = content["application/json"]["schema"]
        return found
    item = content.get("text/event-stream", {}).get("itemSchema", {})
    data = item.get("properties", {}).get("data", {}).get("contentSchema")
    assert isinstance(data, dict), f"{at} has no success response schema"
    return data


def _sample(  # pylint: disable=too-many-return-statements
    schema: Schema, target: Schema, filled: bool
) -> Any:
    """A value matching ``target``.

    With ``filled``, every field and nullable is filled in; without, nullables are null and
    optional fields are left out.
    """
    target = _resolve(schema, target)
    if "anyOf" in target:
        variants = target["anyOf"]
        if not filled and any(v.get("type") == "null" for v in variants):
            return None
        return _sample(schema, next(v for v in variants if v.get("type") != "null"), filled)
    if "enum" in target:
        return target["enum"][0]
    if "const" in target:
        return target["const"]
    kind = target.get("type")
    if kind == "object":
        required = target.get("required", [])
        return {
            name: _sample(schema, field, filled)
            for name, field in target.get("properties", {}).items()
            if filled or name in required
        }
    if kind == "array":
        return [_sample(schema, target["items"], filled)]
    samples = {"string": "2026-11-25T20:00:00", "integer": 1, "number": 1.5, "boolean": True}
    assert kind in samples, f"no sample for schema type {kind!r}"
    return samples[kind]


def _accepts(  # pylint: disable=too-many-return-statements
    schema: Schema, target: Schema, value: Any
) -> bool:
    """Whether ``target`` accepts ``value``: known fields of the right type, required ones."""
    target = _resolve(schema, target)
    if "anyOf" in target:
        return any(_accepts(schema, v, value) for v in target["anyOf"])
    kind = target.get("type")
    if kind == "object" and isinstance(value, dict):
        props = target.get("properties", {})
        return all(k in props and _accepts(schema, props[k], v) for k, v in value.items()) and all(
            r in value for r in target.get("required", [])
        )
    if kind == "array" and isinstance(value, list):
        return all(_accepts(schema, target["items"], v) for v in value)
    if kind == "integer":
        return isinstance(value, int) and not isinstance(value, bool)
    if kind == "number":
        return isinstance(value, (int, float)) and not isinstance(value, bool)
    if kind == "null":
        return value is None
    return {"string": str, "boolean": bool}.get(kind or "") is type(value)


def _resolve(schema: Schema, target: Schema) -> Schema:
    ref = target.get("$ref")
    if ref is None:
        return target
    return _resolve(
        schema, schema["components"]["schemas"][ref.removeprefix("#/components/schemas/")]
    )


def _assert_present(read: Any, sample: Any, at: str) -> None:
    """Every field the plugin read back from ``sample`` is in it, at any depth."""
    if isinstance(read, dict) and isinstance(sample, dict):
        for name, value in read.items():
            assert name in sample, f"{at}: the plugin reads {name!r}, which the schema lacks"
            _assert_present(value, sample[name], f"{at}.{name}")
    elif isinstance(read, list) and isinstance(sample, list):
        for value, given in zip(read, sample):
            _assert_present(value, given, at)
