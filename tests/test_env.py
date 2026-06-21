import pytest
from hud.graders import SubScore
from hud.eval.taskset import Taskset

from cad_description_tasks import tasks as description_tasks
from cad_edit_tasks import tasks as edit_tasks
from llm_judge import (
    DEFAULT_MINIMAX_BASE_URL,
    MiniMaxJudgeGrader,
    _Criterion,
    _Verdict,
    _aggregate,
    _answer_text_for_grading,
    _criteria_from_judge,
    _parse_verdict,
    llm_judge,
)
from mousecad_env import env
from tasks import tasks


def test_env_exists():
    assert env.name == "mousecad"


def test_first_description_task_is_registered():
    assert [task.slug for task in edit_tasks] == ["generate-cube-5cm"]
    assert [task.slug for task in description_tasks] == ["describe-cube-5cm"]
    assert [task.slug for task in tasks] == ["generate-cube-5cm", "describe-cube-5cm"]


def test_taskset_loads_without_duplicate_slugs():
    taskset = Taskset.from_file("tasks.py")
    assert [slug for slug, _ in taskset.items()] == ["generate-cube-5cm", "describe-cube-5cm"]


def test_judge_json_parses_weighted_criteria():
    criteria = _criteria_from_judge(
        {
            "criteria": [
                {"requirement": "mentions cube", "weight": 0.5},
                {"type": "negative", "requirement": "adds holes", "weight": 0.25},
            ]
        }
    )
    assert criteria == [
        ("mentions cube", 0.5),
        ("adds holes", -0.25),
    ]


async def test_llm_judge_template_uses_json_spec(monkeypatch: pytest.MonkeyPatch):
    seen = {}

    async def fake_grade(**kwargs):
        seen.update(kwargs)
        return SubScore(name=kwargs["name"], weight=kwargs["weight"], value=0.75)

    monkeypatch.setattr(MiniMaxJudgeGrader, "grade", fake_grade)

    judge = {
        "name": "test-judge",
        "criteria": [{"requirement": "mentions cube", "weight": 1.0}],
    }
    gen = llm_judge.func(
        prompt="Describe the CAD.",
        judge=judge,
        model="judge-model",
        base_url="https://minimax.test/v1",
    )

    assert await gen.asend(None) == "Describe the CAD."
    result = await gen.asend("It is a cube.")

    assert result.reward == 0.75
    assert result.info["judge"] == judge
    assert seen["answer"] == "It is a cube."
    assert seen["criteria"] == [("mentions cube", 1.0)]
    assert seen["model"] == "judge-model"
    assert seen["base_url"] == "https://minimax.test/v1"
    assert "Judge using this JSON scoring specification" in seen["question"]


async def test_llm_judge_strips_reasoning_before_grading(monkeypatch: pytest.MonkeyPatch):
    seen = {}

    async def fake_grade(**kwargs):
        seen.update(kwargs)
        return SubScore(name=kwargs["name"], weight=kwargs["weight"], value=1.0)

    monkeypatch.setattr(MiniMaxJudgeGrader, "grade", fake_grade)

    gen = llm_judge.func(
        prompt="Describe the CAD.",
        judge={
            "name": "test-judge",
            "criteria": [{"requirement": "mentions cube", "weight": 1.0}],
        },
    )

    assert await gen.asend(None) == "Describe the CAD."
    await gen.asend("<think>parse the sketch</think>\nIt is a 5 cm cube.")

    assert seen["answer"] == "It is a 5 cm cube."


def test_answer_text_for_grading_handles_qwen_reasoning_separator():
    answer = "private reasoning tokens\n</think>\n<tool_call>\n...\n</tool_call>"
    assert _answer_text_for_grading(answer) == "<tool_call>\n...\n</tool_call>"


def test_answer_text_for_grading_prefers_visible_content_field():
    answer = {"content": "<think>hidden</think>\nCylinder", "reasoning_content": "hidden"}
    assert _answer_text_for_grading(answer) == "Cylinder"


def test_default_minimax_base_url_is_openai_compatible():
    assert DEFAULT_MINIMAX_BASE_URL == "https://api.minimax.io/v1"


def test_parse_verdict_json():
    met, reason = _parse_verdict('{"criterion_status": "MET", "explanation": "ok"}')
    assert met is True
    assert reason == "ok"


def test_negative_criteria_penalize_score():
    score = _aggregate(
        [
            _Verdict(_Criterion("identifies cube", 1.0), met=True, reason="ok"),
            _Verdict(_Criterion("hallucinates holes", -0.25), met=True, reason="bad"),
        ]
    )
    assert score == 0.75
