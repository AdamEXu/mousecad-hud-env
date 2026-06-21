from __future__ import annotations

import ast
import math
import re
from collections.abc import Iterable
from dataclasses import dataclass
from typing import Any

from cad_dsl import (
    LLM_TOOL_FUNCTIONS,
    Operation,
    Recorder,
    Ref,
    curve,
    done,
    feature,
    profile,
    ref,
    set_recorder,
    sketch,
)


TOOL_CALL_FUNCTION = "predict_cad_template"
TOOL_CALL_PARAMETER = "template"
_THINK_BLOCK_RE = re.compile(r"<think\b[^>]*>.*?</think\s*>", re.IGNORECASE | re.DOTALL)
_TOOL_CALL_RE = re.compile(
    r"\A<tool_call>\n"
    r"<function=predict_cad_template>\n"
    r"<parameter=template>\n"
    r"(?P<template>.*)\n"
    r"</parameter>\n"
    r"</function>\n"
    r"</tool_call>\Z",
    re.DOTALL,
)


@dataclass(frozen=True)
class Execution:
    template: str
    operations: list[Operation]


@dataclass(frozen=True)
class Grade:
    reward: float
    details: dict[str, Any]


def grade_answer(answer: str | Any, spec: dict[str, Any]) -> Grade:
    visible = _answer_text(answer)
    template = _parse_wrapper(visible)
    if template is None:
        return Grade(0.0, {"stage": "format", "error": "response must be exactly one predict_cad_template tool call"})

    execution, error = _execute_template(template)
    if error:
        return Grade(0.0, {"stage": "execution", "error": error})

    assert execution is not None
    procedure_score, procedure_details = _score_procedure(execution.operations)
    if spec.get("reference_template"):
        task_score, task_details = _score_reference_template(execution.operations, spec)
    else:
        task_score, task_details = _score_task(execution.operations, spec)
    reward = round(0.15 * procedure_score + 0.85 * task_score, 6)
    return Grade(
        reward,
        {
            "stage": "scored",
            "format": 1.0,
            "execution": 1.0,
            "procedure_score": procedure_score,
            "task_score": task_score,
            "procedure": procedure_details,
            "task": task_details,
        },
    )


def _answer_text(answer: str | Any) -> str:
    if answer is None:
        return ""
    if isinstance(answer, dict):
        content = answer.get("content")
        if isinstance(content, str):
            return _strip_reasoning(content)
        message = answer.get("message")
        if isinstance(message, dict) and isinstance(message.get("content"), str):
            return _strip_reasoning(str(message["content"]))
    content_attr = getattr(answer, "content", None)
    if isinstance(content_attr, str):
        return _strip_reasoning(content_attr)
    return _strip_reasoning(str(answer))


def _strip_reasoning(text: str) -> str:
    cleaned = _THINK_BLOCK_RE.sub("", text.replace("\r\n", "\n")).strip()
    close_index = cleaned.lower().rfind("</think>")
    if close_index != -1:
        cleaned = cleaned[close_index + len("</think>") :].strip()
    return cleaned


def _parse_wrapper(text: str) -> str | None:
    match = _TOOL_CALL_RE.match(text)
    if not match:
        return None
    template = match.group("template")
    if not template.strip():
        return None
    return template


def _execute_template(template: str) -> tuple[Execution | None, str | None]:
    try:
        tree = ast.parse(template, mode="exec")
    except SyntaxError as exc:
        return None, f"invalid Python syntax: {exc.msg}"

    safety_error = _validate_ast(tree)
    if safety_error:
        return None, safety_error

    recorder = Recorder()
    safe_globals = {
        "__builtins__": {},
        "ref": ref,
        "sketch": sketch,
        "curve": curve,
        "done": done,
        "profile": profile,
        "feature": feature,
    }
    try:
        set_recorder(recorder)
        exec(compile(tree, "<cad-template>", "exec"), safe_globals, {})
    except Exception as exc:
        return None, f"template raised {type(exc).__name__}: {exc}"
    finally:
        set_recorder(None)

    return Execution(template=template, operations=recorder.operations), None


def _validate_ast(tree: ast.AST) -> str | None:
    allowed_nodes = (
        ast.Module,
        ast.Assign,
        ast.Expr,
        ast.Call,
        ast.Name,
        ast.Load,
        ast.Store,
        ast.Constant,
        ast.Tuple,
        ast.List,
        ast.keyword,
        ast.UnaryOp,
        ast.USub,
    )
    for node in ast.walk(tree):
        if not isinstance(node, allowed_nodes):
            return f"disallowed Python node: {type(node).__name__}"
        if isinstance(node, ast.Call):
            if not isinstance(node.func, ast.Name) or node.func.id not in LLM_TOOL_FUNCTIONS:
                return "only CAD DSL function calls are allowed"
        if isinstance(node, ast.Assign) and len(node.targets) != 1:
            return "multiple assignment is not allowed"
    return None


def _score_procedure(operations: list[Operation]) -> tuple[float, dict[str, Any]]:
    refs = [op for op in operations if op.function == "ref"]
    sketches = [op for op in operations if op.function == "sketch"]
    curves = [op for op in operations if op.function == "curve"]
    dones = [op for op in operations if op.function == "done"]
    profiles = [op for op in operations if op.function == "profile"]
    features = [op for op in operations if op.function == "feature"]

    checks = {
        "has_reference": bool(refs),
        "has_sketch": bool(sketches),
        "has_curves": bool(curves),
        "has_done": bool(dones),
        "has_profile": bool(profiles),
        "has_extrude": any(op.args and op.args[0] == "extrude" for op in features),
        "all_profiles_after_done": _profiles_after_done(operations),
        "all_extrudes_target_profiles": _extrudes_target_profiles(features),
        "closed_profiles": bool(_recognized_profiles(operations)),
    }
    score = sum(1.0 for value in checks.values() if value) / len(checks)
    return round(score, 6), checks


def _profiles_after_done(operations: list[Operation]) -> bool:
    done_indices = {
        op.args[0].name: index
        for index, op in enumerate(operations)
        if op.function == "done" and op.args and isinstance(op.args[0], Ref)
    }
    profiles = [(index, op) for index, op in enumerate(operations) if op.function == "profile"]
    return bool(profiles) and all(
        op.args and isinstance(op.args[0], Ref) and done_indices.get(op.args[0].name, 10**9) < index
        for index, op in profiles
    )


def _extrudes_target_profiles(features: Iterable[Operation]) -> bool:
    seen = False
    for op in features:
        if not op.args or op.args[0] != "extrude":
            continue
        seen = True
        target = op.args[1] if len(op.args) > 1 else None
        if not isinstance(target, Ref) or target.kind != "profile":
            return False
    return seen


def _score_reference_template(operations: list[Operation], spec: dict[str, Any]) -> tuple[float, dict[str, Any]]:
    reference_template = spec.get("reference_template")
    if not isinstance(reference_template, str) or not reference_template.strip():
        return 0.0, {"error": "task spec has no reference_template"}

    reference, error = _execute_template(reference_template)
    if error or reference is None:
        return 0.0, {"error": f"reference template is invalid: {error}"}

    return _compare_operations(operations, reference.operations)


def _compare_operations(actual: list[Operation], expected: list[Operation]) -> tuple[float, dict[str, Any]]:
    if not expected:
        return 0.0, {"error": "reference template produced no operations"}

    pair_count = min(len(actual), len(expected))
    operation_scores: list[dict[str, Any]] = []
    for index in range(pair_count):
        score, details = _compare_operation(actual[index], expected[index])
        operation_scores.append({"index": index, "score": score, **details})

    matched_score = sum(item["score"] for item in operation_scores) / len(expected)
    missing_penalty = max(0, len(expected) - len(actual)) / len(expected)
    extra_penalty = max(0, len(actual) - len(expected)) / max(len(actual), 1)
    score = max(0.0, matched_score - 0.35 * missing_penalty - 0.2 * extra_penalty)

    scale_failures = [
        item
        for item in operation_scores
        if item.get("has_scale_fields") and item.get("scale_score", 0.0) < 1.0
    ]
    if scale_failures:
        score = min(score, 0.35)

    return round(score, 6), {
        "mode": "reference_template",
        "expected_count": len(expected),
        "actual_count": len(actual),
        "missing_count": max(0, len(expected) - len(actual)),
        "extra_count": max(0, len(actual) - len(expected)),
        "scale_failures": len(scale_failures),
        "operations": operation_scores[:50],
    }


def _compare_operation(actual: Operation, expected: Operation) -> tuple[float, dict[str, Any]]:
    function_ok = actual.function == expected.function
    result_kind_ok = actual.result.kind == expected.result.kind
    result_name_ok = actual.result.name == expected.result.name
    args_score, args_details = _compare_value(actual.args, expected.args)
    kwargs_score, kwargs_details, scale_score, has_scale_fields = _compare_kwargs(actual.kwargs, expected.kwargs)

    weighted = {
        "function": (1.0 if function_ok else 0.0, 0.18),
        "result_kind": (1.0 if result_kind_ok else 0.0, 0.08),
        "result_name": (1.0 if result_name_ok else 0.0, 0.06),
        "args": (args_score, 0.23),
        "kwargs": (kwargs_score, 0.45),
    }
    total = sum(value * weight for value, weight in weighted.values())
    if has_scale_fields and scale_score < 1.0:
        total = min(total, 0.35)

    return round(total, 6), {
        "function": actual.function,
        "expected_function": expected.function,
        "function_ok": function_ok,
        "result_kind_ok": result_kind_ok,
        "result_name_ok": result_name_ok,
        "args": args_details,
        "kwargs": kwargs_details,
        "scale_score": scale_score,
        "has_scale_fields": has_scale_fields,
    }


def _compare_kwargs(
    actual: dict[str, Any],
    expected: dict[str, Any],
) -> tuple[float, dict[str, Any], float, bool]:
    keys = sorted(set(actual) | set(expected))
    if not keys:
        return 1.0, {"keys": []}, 1.0, False

    scale_keys = {"distance", "radius", "thickness", "spacing", "start", "end", "center", "corner1", "corner2", "mid"}
    details: dict[str, Any] = {"keys": []}
    weighted_total = 0.0
    total_weight = 0.0
    scale_total = 0.0
    scale_weight = 0.0
    for key in keys:
        value_score, value_details = _compare_value(actual.get(key), expected.get(key))
        weight = 5.0 if key in scale_keys else 1.0
        weighted_total += value_score * weight
        total_weight += weight
        if key in scale_keys:
            scale_total += value_score * weight
            scale_weight += weight
        details["keys"].append({"key": key, "score": round(value_score, 6), "details": value_details})

    scale_score = 1.0 if scale_weight == 0 else scale_total / scale_weight
    return weighted_total / total_weight, details, round(scale_score, 6), scale_weight > 0


def _compare_value(actual: Any, expected: Any) -> tuple[float, dict[str, Any]]:
    if isinstance(expected, Ref):
        ok = isinstance(actual, Ref) and actual.kind == expected.kind and actual.name == expected.name
        return (1.0 if ok else 0.0), {"expected": _value_label(expected), "actual": _value_label(actual)}

    if _is_number(expected):
        ok = _same_measure(actual, expected)
        return (1.0 if ok else 0.0), {"expected": expected, "actual": actual, "scale_match": ok}

    if isinstance(expected, tuple):
        if not isinstance(actual, tuple) or len(actual) != len(expected):
            return 0.0, {"expected": _value_label(expected), "actual": _value_label(actual)}
        scores = [_compare_value(a, e)[0] for a, e in zip(actual, expected)]
        return sum(scores) / len(scores), {"expected": expected, "actual": actual, "item_scores": scores}

    if isinstance(expected, list):
        if not isinstance(actual, list) or len(actual) != len(expected):
            return 0.0, {"expected": _value_label(expected), "actual": _value_label(actual)}
        if not expected:
            return 1.0, {"expected": [], "actual": []}
        scores = [_compare_value(a, e)[0] for a, e in zip(actual, expected)]
        return sum(scores) / len(scores), {"expected": _value_label(expected), "actual": _value_label(actual), "item_scores": scores}

    ok = actual == expected
    return (1.0 if ok else 0.0), {"expected": expected, "actual": actual}


def _value_label(value: Any) -> Any:
    if isinstance(value, Ref):
        return {"kind": value.kind, "name": value.name}
    if isinstance(value, tuple):
        return tuple(_value_label(item) for item in value)
    if isinstance(value, list):
        return [_value_label(item) for item in value]
    return value


def _score_task(operations: list[Operation], spec: dict[str, Any]) -> tuple[float, dict[str, Any]]:
    expected = spec.get("expected_bodies", [])
    if not isinstance(expected, list) or not expected:
        return 0.0, {"error": "task spec has no expected bodies"}

    built = _built_bodies(operations)
    matched: list[dict[str, Any]] = []
    used: set[int] = set()
    for body_spec in expected:
        best_index = None
        best_score = -1.0
        best_details: dict[str, Any] = {}
        for index, body in enumerate(built):
            if index in used:
                continue
            score, details = _match_body(body, body_spec)
            if score > best_score:
                best_index = index
                best_score = score
                best_details = details
        if best_index is not None:
            used.add(best_index)
        matched.append({"expected": body_spec, "score": max(0.0, best_score), "details": best_details})

    shape_score = sum(item["score"] for item in matched) / len(expected)
    extra_penalty = max(0, len(built) - len(expected)) * 0.1
    score = max(0.0, min(1.0, shape_score - extra_penalty))
    return round(score, 6), {"expected_count": len(expected), "built_count": len(built), "matches": matched}


def _built_bodies(operations: list[Operation]) -> list[dict[str, Any]]:
    profiles = _recognized_profiles(operations)
    bodies: list[dict[str, Any]] = []
    for op in operations:
        if op.function != "feature" or not op.args or op.args[0] != "extrude":
            continue
        target = op.args[1] if len(op.args) > 1 else None
        if not isinstance(target, Ref):
            continue
        profile_info = profiles.get(target.name)
        if not profile_info:
            continue
        bodies.append(
            {
                "name": op.args[2] if len(op.args) > 2 else op.result.name,
                "profile": profile_info,
                "distance": op.kwargs.get("distance"),
                "mode": op.kwargs.get("mode", "new"),
            }
        )
    return bodies


def _recognized_profiles(operations: list[Operation]) -> dict[str, dict[str, Any]]:
    sketch_sources: dict[str, Ref] = {}
    sketch_curves: dict[str, list[Operation]] = {}
    profiles: dict[str, dict[str, Any]] = {}
    done_sketches: set[str] = set()

    for op in operations:
        if op.function == "sketch" and op.args and isinstance(op.args[0], Ref):
            sketch_sources[op.result.name] = op.args[0]
        elif op.function == "curve" and op.args and isinstance(op.args[0], Ref):
            sketch_curves.setdefault(op.args[0].name, []).append(op)
        elif op.function == "done" and op.args and isinstance(op.args[0], Ref):
            done_sketches.add(op.args[0].name)
        elif op.function == "profile" and op.args and isinstance(op.args[0], Ref):
            sketch_name = op.args[0].name
            shape = _recognize_shape(sketch_curves.get(sketch_name, []))
            if shape and sketch_name in done_sketches:
                profiles[op.result.name] = {
                    **shape,
                    "sketch": sketch_name,
                    "on": sketch_sources.get(sketch_name),
                }
    return profiles


def _recognize_shape(curves: list[Operation]) -> dict[str, Any] | None:
    real_curves = [op for op in curves if not op.kwargs.get("construction")]
    if len(real_curves) == 1:
        op = real_curves[0]
        if len(op.args) >= 2 and op.args[1] == "circle" and _is_number(op.kwargs.get("radius")):
            return {"shape": "circle", "radius": float(op.kwargs["radius"])}

    points: list[tuple[float, float]] = []
    for op in real_curves:
        if len(op.args) < 2 or op.args[1] != "line":
            return None
        start = _point(op.kwargs.get("start"))
        end = _point(op.kwargs.get("end"))
        if start is None or end is None:
            return None
        if points and not _same_point(points[-1], start):
            return None
        if not points:
            points.append(start)
        points.append(end)

    if len(points) < 4 or not _same_point(points[0], points[-1]):
        return None
    vertices = points[:-1]
    sides = [_distance(vertices[index], vertices[(index + 1) % len(vertices)]) for index in range(len(vertices))]
    if len(vertices) == 3:
        return {"shape": "equilateral_triangle", "side": sum(sides) / 3, "sides": sides}
    if len(vertices) == 4:
        width = max(point[0] for point in vertices) - min(point[0] for point in vertices)
        height = max(point[1] for point in vertices) - min(point[1] for point in vertices)
        if _close(width, height):
            return {"shape": "square", "side": (width + height) / 2, "width": width, "height": height}
        return {"shape": "rectangle", "width": width, "height": height, "sides": sides}
    return {"shape": "polygon", "sides": sides}


def _match_body(body: dict[str, Any], spec: dict[str, Any]) -> tuple[float, dict[str, Any]]:
    profile = body["profile"]
    weighted_checks: dict[str, tuple[bool, float]] = {
        "shape": (profile.get("shape") == spec.get("shape"), 0.2),
        "mode": (body.get("mode") == spec.get("mode", body.get("mode")), 0.1),
    }
    scale_checks: dict[str, bool] = {
        "distance": _same_measure(body.get("distance"), spec.get("distance")),
    }

    if "side" in spec:
        scale_checks["side"] = _same_measure(profile.get("side"), spec["side"])
    if "width" in spec:
        scale_checks["width"] = _same_measure(profile.get("width"), spec["width"])
    if "height" in spec:
        scale_checks["height"] = _same_measure(profile.get("height"), spec["height"])
    if "radius" in spec:
        scale_checks["radius"] = _same_measure(profile.get("radius"), spec["radius"])
    scale_weight = 0.7 / len(scale_checks)
    for name, passed in scale_checks.items():
        weighted_checks[name] = (passed, scale_weight)

    if spec.get("on_top_of"):
        source = profile.get("on")
        weighted_checks["on_top_of"] = (
            isinstance(source, Ref)
            and source.kind == "face"
            and str(spec["on_top_of"]) in source.name
            and "top" in source.name.lower(),
            0.1,
        )

    total_weight = sum(weight for _, weight in weighted_checks.values())
    score = sum(weight for passed, weight in weighted_checks.values() if passed) / total_weight
    if not all(scale_checks.values()):
        score = min(score, 0.25)

    return round(score, 6), {
        "body": body["name"],
        "checks": {name: passed for name, (passed, _) in weighted_checks.items()},
        "scale_checks": scale_checks,
    }


def _point(value: Any) -> tuple[float, float] | None:
    if (
        isinstance(value, tuple)
        and len(value) == 2
        and _is_number(value[0])
        and _is_number(value[1])
    ):
        return float(value[0]), float(value[1])
    return None


def _is_number(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def _distance(a: tuple[float, float], b: tuple[float, float]) -> float:
    return math.hypot(a[0] - b[0], a[1] - b[1])


def _same_point(a: tuple[float, float], b: tuple[float, float]) -> bool:
    return _close(a[0], b[0]) and _close(a[1], b[1])


def _same_measure(actual: Any, expected: Any) -> bool:
    return _is_number(actual) and _is_number(expected) and _close(float(actual), float(expected))


def _close(a: float, b: float, *, rel_tol: float = 1e-3, abs_tol: float = 1e-3) -> bool:
    return math.isclose(a, b, rel_tol=rel_tol, abs_tol=abs_tol)
