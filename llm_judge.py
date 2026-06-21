from __future__ import annotations

import json
from typing import Any

from hud.graders import EvaluationResult, LLMJudgeGrader

from mousecad_env import env

DEFAULT_JUDGE_MODEL = "claude-haiku-4-5"


@env.template(id="llm-judge")
async def llm_judge(
    prompt: str,
    judge: dict[str, Any],
    model: str = DEFAULT_JUDGE_MODEL,
):
    answer = yield prompt
    subscore = await LLMJudgeGrader.grade(
        weight=1.0,
        name=str(judge.get("name", "llm-judge")),
        answer=answer or "",
        criteria=_criteria_from_judge(judge),
        question=_judge_question(prompt, judge),
        model=model,
    )
    yield EvaluationResult(
        reward=subscore.value,
        done=True,
        subscores=[subscore],
        info={"judge": judge, "model": model},
    )


def _criteria_from_judge(judge: dict[str, Any]) -> list[str | tuple[str, float]]:
    criteria = judge.get("criteria")
    if not isinstance(criteria, list) or not criteria:
        raise ValueError("judge must contain a non-empty 'criteria' list")

    parsed: list[str | tuple[str, float]] = []
    for item in criteria:
        if isinstance(item, str):
            parsed.append(item)
            continue
        if not isinstance(item, dict):
            raise TypeError("judge criteria must be strings or objects")

        requirement = item.get("requirement") or item.get("criterion") or item.get("description")
        if not requirement:
            raise ValueError("judge criterion object must include 'requirement'")

        weight = float(item.get("weight", 1.0))
        criterion_type = str(item.get("type", item.get("criterion_type", "positive"))).lower()
        if criterion_type == "negative" and weight > 0:
            weight = -weight

        parsed.append((str(requirement), weight))

    return parsed


def _judge_question(prompt: str, judge: dict[str, Any]) -> str:
    return (
        f"{prompt}\n\n"
        "Judge using this JSON scoring specification:\n"
        f"{json.dumps(judge, indent=2, sort_keys=True)}"
    )
