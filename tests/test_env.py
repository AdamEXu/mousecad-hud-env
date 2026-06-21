import pytest
from hud.graders import SubScore

from cad_description_tasks import tasks as description_tasks
from cad_edit_tasks import tasks as edit_tasks
from llm_judge import LLMJudgeGrader, _criteria_from_judge, llm_judge
from mousecad_env import env
from tasks import tasks


def test_env_exists():
    assert env.name == "mousecad"


def test_first_description_task_is_registered():
    assert edit_tasks == []
    assert [task.slug for task in description_tasks] == ["describe-cube-10cm"]
    assert [task.slug for task in tasks] == ["describe-cube-10cm"]


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

    monkeypatch.setattr(LLMJudgeGrader, "grade", fake_grade)

    judge = {
        "name": "test-judge",
        "criteria": [{"requirement": "mentions cube", "weight": 1.0}],
    }
    gen = llm_judge.func(prompt="Describe the CAD.", judge=judge, model="judge-model")

    assert await gen.asend(None) == "Describe the CAD."
    result = await gen.asend("It is a cube.")

    assert result.reward == 0.75
    assert result.info["judge"] == judge
    assert seen["answer"] == "It is a cube."
    assert seen["criteria"] == [("mentions cube", 1.0)]
    assert seen["model"] == "judge-model"
    assert "Judge using this JSON scoring specification" in seen["question"]
