from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal, Sequence


Number = int | float
Point2D = tuple[Number, Number]
Vector3D = tuple[Number, Number, Number]

RefKind = Literal["body", "face", "edge", "plane", "axis", "feature", "sketch", "profile", "curve"]
CurveKind = Literal["line", "arc", "circle", "rect"]
FeatureKind = Literal["extrude", "revolve", "fillet", "chamfer", "shell", "mirror", "pattern", "boolean"]
BoolMode = Literal["new", "add", "cut", "intersect"]


@dataclass(frozen=True)
class Ref:
    kind: str
    name: str


@dataclass(frozen=True)
class Operation:
    function: str
    result: Ref
    args: tuple[Any, ...]
    kwargs: dict[str, Any]


class Recorder:
    def __init__(self) -> None:
        self.operations: list[Operation] = []

    def record(self, function: str, result: Ref, *args: Any, **kwargs: Any) -> Ref:
        self.operations.append(Operation(function=function, result=result, args=args, kwargs=kwargs))
        return result


_active_recorder: Recorder | None = None


def set_recorder(recorder: Recorder | None) -> None:
    global _active_recorder
    _active_recorder = recorder


def _record(function: str, result: Ref, *args: Any, **kwargs: Any) -> Ref:
    if _active_recorder is not None:
        return _active_recorder.record(function, result, *args, **kwargs)
    return result


def ref(kind: RefKind, name: str) -> Ref:
    """Reference an existing CAD object by kind and name."""

    return _record("ref", Ref(kind, name), kind, name)


def sketch(on: Ref, name: str, *, origin: Point2D = (0, 0)) -> Ref:
    """Create a sketch on a plane or planar face."""

    return _record("sketch", Ref("sketch", name), on, name, origin=origin)


def curve(
    sketch_ref: Ref,
    kind: CurveKind,
    name: str,
    *,
    start: Point2D | None = None,
    end: Point2D | None = None,
    center: Point2D | None = None,
    radius: Number | None = None,
    corner1: Point2D | None = None,
    corner2: Point2D | None = None,
    mid: Point2D | None = None,
    construction: bool = False,
) -> Ref:
    """Add one sketch curve: line, arc, circle, or rect."""

    return _record(
        "curve",
        Ref("curve", name),
        sketch_ref,
        kind,
        name,
        start=start,
        end=end,
        center=center,
        radius=radius,
        corner1=corner1,
        corner2=corner2,
        mid=mid,
        construction=construction,
    )


def done(sketch_ref: Ref) -> Ref:
    """Finish a sketch so closed regions can be selected."""

    return _record("done", sketch_ref, sketch_ref)


def profile(sketch_ref: Ref, name: str, *, hint: str | None = None) -> Ref:
    """Select a closed sketch region for 3D features."""

    return _record("profile", Ref("profile", name), sketch_ref, name, hint=hint)


def feature(
    kind: FeatureKind,
    targets: Ref | Sequence[Ref],
    name: str,
    *,
    distance: Number | str | tuple[Number | str, Number | str] | None = None,
    mode: BoolMode = "new",
    axis: Ref | Vector3D | None = None,
    angle: Number | str | None = None,
    radius: Number | str | None = None,
    thickness: Number | str | None = None,
    plane: Ref | None = None,
    count: int | None = None,
    spacing: Number | str | None = None,
    operation: Literal["union", "subtract", "intersect"] | None = None,
    tool: Ref | Sequence[Ref] | None = None,
) -> Ref:
    """Apply a 3D feature such as extrude, fillet, mirror, pattern, or boolean."""

    result_kind = "body" if kind == "extrude" else "feature"
    return _record(
        "feature",
        Ref(result_kind, name),
        kind,
        targets,
        name,
        distance=distance,
        mode=mode,
        axis=axis,
        angle=angle,
        radius=radius,
        thickness=thickness,
        plane=plane,
        count=count,
        spacing=spacing,
        operation=operation,
        tool=tool,
    )


LLM_TOOL_FUNCTIONS = ("ref", "sketch", "curve", "done", "profile", "feature")

__all__ = [
    "Number",
    "Point2D",
    "Vector3D",
    "RefKind",
    "CurveKind",
    "FeatureKind",
    "BoolMode",
    "Ref",
    "Operation",
    "Recorder",
    "set_recorder",
    "LLM_TOOL_FUNCTIONS",
    *LLM_TOOL_FUNCTIONS,
]
