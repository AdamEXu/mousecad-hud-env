import pytest
from hud.eval.taskset import Taskset

from cad_description_tasks import tasks as description_tasks
from cad_edit_tasks import tasks as edit_tasks
from cad_reward import _answer_text, grade_answer
from mousecad_env import env
from tasks import tasks


CUBE_SPEC = {
    "slug": "make-cube-5cm",
    "expected_bodies": [
        {
            "shape": "square",
            "side": 50.0,
            "distance": 50.0,
            "mode": "new",
        }
    ],
}


def wrap(template: str) -> str:
    return (
        "<tool_call>\n"
        "<function=predict_cad_template>\n"
        "<parameter=template>\n"
        f"{template}\n"
        "</parameter>\n"
        "</function>\n"
        "</tool_call>"
    )


def test_env_exists():
    assert env.name == "mousecad"


def test_template_tasks_are_registered():
    assert [task.slug for task in edit_tasks] == [
        "make-cube-5cm",
        "make-equilateral-triangle-prism-5cm",
        "make-cube-5cm-with-top-triangle-2cm",
        "make-cylinder-3cm-diameter-5cm-tall",
        "make-rectangular-prism-5cm-3cm-2cm",
    ]
    assert description_tasks == []
    assert [task.slug for task in tasks] == [task.slug for task in edit_tasks]


def test_taskset_loads_without_duplicate_slugs():
    taskset = Taskset.from_file("tasks.py")
    assert [slug for slug, _ in taskset.items()] == [task.slug for task in edit_tasks]


def test_bad_wrapper_scores_zero():
    result = grade_answer("s1 = sketch(ref('plane', 'plane_1'), 'sketch_1')", CUBE_SPEC)
    assert result.reward == 0.0
    assert result.details["stage"] == "format"


def test_disallowed_python_scores_zero():
    result = grade_answer(wrap("import os\nos.getcwd()"), CUBE_SPEC)
    assert result.reward == 0.0
    assert result.details["stage"] == "execution"


def test_qwen_reasoning_is_removed_before_format_check():
    answer = "<think>hidden reasoning</think>\n" + wrap("s1 = sketch(ref('plane', 'plane_1'), 'sketch_1')")
    assert _answer_text(answer).startswith("<tool_call>")


def test_cube_template_scores_full_reward():
    answer = wrap(
        "\n".join(
            [
                "s1 = sketch(ref('plane', 'plane_1'), 'sketch_1')",
                "e1 = curve(s1, 'line', 'e1', start=(0, 0), end=(50, 0))",
                "e2 = curve(s1, 'line', 'e2', start=(50, 0), end=(50, 50))",
                "e3 = curve(s1, 'line', 'e3', start=(50, 50), end=(0, 50))",
                "e4 = curve(s1, 'line', 'e4', start=(0, 50), end=(0, 0))",
                "done(s1)",
                "p1 = profile(s1, 'profile_1')",
                "b1 = feature('extrude', p1, 'body_1', distance=50, mode='new')",
            ]
        )
    )
    result = grade_answer(answer, CUBE_SPEC)
    assert result.reward == 1.0
    assert result.details["procedure_score"] == 1.0
    assert result.details["task_score"] == 1.0


def test_wrong_dimension_gets_partial_reward_after_execution_gate():
    answer = wrap(
        "\n".join(
            [
                "s1 = sketch(ref('plane', 'plane_1'), 'sketch_1')",
                "e1 = curve(s1, 'line', 'e1', start=(0, 0), end=(25, 0))",
                "e2 = curve(s1, 'line', 'e2', start=(25, 0), end=(25, 25))",
                "e3 = curve(s1, 'line', 'e3', start=(25, 25), end=(0, 25))",
                "e4 = curve(s1, 'line', 'e4', start=(0, 25), end=(0, 0))",
                "done(s1)",
                "p1 = profile(s1, 'profile_1')",
                "b1 = feature('extrude', p1, 'body_1', distance=50, mode='new')",
            ]
        )
    )
    result = grade_answer(answer, CUBE_SPEC)
    assert 0.0 < result.reward <= 0.4


def test_reference_template_scores_full_reward():
    template = "\n".join(
        [
            "s1 = sketch(ref('plane', 'plane_1'), 'patch_sketch_1')",
            "e1 = curve(s1, 'line', 'e1', start=(128, 128), end=(152, 33))",
            "e2 = curve(s1, 'line', 'e2', start=(152, 33), end=(171, 38))",
            "e3 = curve(s1, 'line', 'e3', start=(171, 38), end=(146, 133))",
            "e4 = curve(s1, 'line', 'e4', start=(146, 133), end=(128, 128))",
            "done(s1)",
            "p1 = profile(s1, 'patch_profile_1')",
            "b1 = feature('extrude', p1, 'body_1', distance=78.125, mode='add')",
        ]
    )
    result = grade_answer(wrap(template), {"reference_template": template})
    assert result.reward == 1.0
    assert result.details["task"]["mode"] == "reference_template"


def test_reference_template_scale_mismatch_is_capped():
    expected = "\n".join(
        [
            "s1 = sketch(ref('plane', 'plane_1'), 'patch_sketch_1')",
            "e1 = curve(s1, 'line', 'e1', start=(128, 128), end=(152, 33))",
            "e2 = curve(s1, 'line', 'e2', start=(152, 33), end=(171, 38))",
            "e3 = curve(s1, 'line', 'e3', start=(171, 38), end=(146, 133))",
            "e4 = curve(s1, 'line', 'e4', start=(146, 133), end=(128, 128))",
            "done(s1)",
            "p1 = profile(s1, 'patch_profile_1')",
            "b1 = feature('extrude', p1, 'body_1', distance=78.125, mode='add')",
        ]
    )
    wrong_scale = expected.replace("distance=78.125", "distance=7.8125")
    result = grade_answer(wrap(wrong_scale), {"reference_template": expected})
    assert 0.0 < result.reward <= 0.45
    assert result.details["task"]["scale_failures"] >= 1


@pytest.mark.parametrize(
    ("slug", "answer"),
    [
        (
            "make-cube-5cm-with-top-triangle-2cm",
            wrap(
                "\n".join(
                    [
                        "s1 = sketch(ref('plane', 'plane_1'), 'sketch_1')",
                        "e1 = curve(s1, 'line', 'e1', start=(0, 0), end=(50, 0))",
                        "e2 = curve(s1, 'line', 'e2', start=(50, 0), end=(50, 50))",
                        "e3 = curve(s1, 'line', 'e3', start=(50, 50), end=(0, 50))",
                        "e4 = curve(s1, 'line', 'e4', start=(0, 50), end=(0, 0))",
                        "done(s1)",
                        "p1 = profile(s1, 'profile_1')",
                        "b1 = feature('extrude', p1, 'body_1', distance=50, mode='new')",
                        "s2 = sketch(ref('face', 'body_1_top'), 'sketch_2')",
                        "e5 = curve(s2, 'line', 'e5', start=(0, 0), end=(20, 0))",
                        "e6 = curve(s2, 'line', 'e6', start=(20, 0), end=(10, 17.320508))",
                        "e7 = curve(s2, 'line', 'e7', start=(10, 17.320508), end=(0, 0))",
                        "done(s2)",
                        "p2 = profile(s2, 'profile_2')",
                        "b2 = feature('extrude', p2, 'body_2', distance=20, mode='add')",
                    ]
                )
            ),
        )
    ],
)
def test_composite_template_scores_full_reward(slug: str, answer: str):
    task = next(item for item in edit_tasks if item.slug == slug)
    spec = task.args["spec"]
    assert grade_answer(answer, spec).reward == 1.0
