from __future__ import annotations

from dataclasses import dataclass

from prompts import build_prompt


@dataclass(frozen=True)
class CADTemplateTask:
    slug: str
    prompt: str
    spec: dict


def _task(slug: str, user_request: str, expected_bodies: list[dict]) -> CADTemplateTask:
    return CADTemplateTask(
        slug=slug,
        prompt=build_prompt(user_request),
        spec={
            "slug": slug,
            "user_request": user_request,
            "expected_bodies": expected_bodies,
        },
    )


_cube_5cm = _task(
    "make-cube-5cm",
    "Make a cube 5 centimeters by 5 centimeters by 5 centimeters.",
    [
        {
            "shape": "square",
            "side": 50.0,
            "distance": 50.0,
            "mode": "new",
        }
    ],
)

_triangle_prism_5cm = _task(
    "make-equilateral-triangle-prism-5cm",
    "Make an equilateral triangular prism with a 5 centimeter by 5 centimeter by 5 centimeter size.",
    [
        {
            "shape": "equilateral_triangle",
            "side": 50.0,
            "distance": 50.0,
            "mode": "new",
        }
    ],
)

_cube_with_top_triangle = _task(
    "make-cube-5cm-with-top-triangle-2cm",
    (
        "Make a cube 5 centimeters by 5 centimeters by 5 centimeters, and on top of it add an "
        "equilateral triangular prism with 2 centimeter side width and 2 centimeter height."
    ),
    [
        {
            "shape": "square",
            "side": 50.0,
            "distance": 50.0,
            "mode": "new",
        },
        {
            "shape": "equilateral_triangle",
            "side": 20.0,
            "distance": 20.0,
            "mode": "add",
            "on_top_of": "body_1",
        },
    ],
)

_cylinder_3cm_diameter_5cm_tall = _task(
    "make-cylinder-3cm-diameter-5cm-tall",
    "Make a cylinder with a 3 centimeter diameter and 5 centimeter height.",
    [
        {
            "shape": "circle",
            "radius": 15.0,
            "distance": 50.0,
            "mode": "new",
        }
    ],
)

_rectangular_prism_5x3x2cm = _task(
    "make-rectangular-prism-5cm-3cm-2cm",
    "Make a rectangular prism 5 centimeters long, 3 centimeters wide, and 2 centimeters tall.",
    [
        {
            "shape": "rectangle",
            "width": 50.0,
            "height": 30.0,
            "distance": 20.0,
            "mode": "new",
        }
    ],
)

tasks = [
    _cube_5cm,
    _triangle_prism_5cm,
    _cube_with_top_triangle,
    _cylinder_3cm_diameter_5cm_tall,
    _rectangular_prism_5x3x2cm,
]
