from __future__ import annotations

import asyncio
import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from hud.graders import EvaluationResult, Grader

from mousecad_env import env
from prompts import JUDGE_SYSTEM_PROMPT

DEFAULT_MINIMAX_BASE_URL = "https://api.minimax.io/v1"
DEFAULT_JUDGE_MODEL = "MiniMax-M3"


@dataclass(slots=True)
class _Criterion:
    requirement: str
    weight: float


@dataclass(slots=True)
class _Verdict:
    criterion: _Criterion
    met: bool
    reason: str


class MiniMaxJudgeGrader(Grader):
    name = "MiniMaxJudgeGrader"

    @classmethod
    async def compute_score(
        cls,
        answer: str | Any = "",
        criteria: list[str | tuple[str, float]] | None = None,
        question: str = "",
        model: str | None = None,
        base_url: str | None = None,
        api_key: str | None = None,
        **kwargs: Any,
    ) -> tuple[float, dict[str, Any]]:
        del kwargs
        parsed = _parse_criteria(criteria)
        if not parsed:
            return 0.0, {"error": "no criteria provided"}

        client = _minimax_client(api_key=api_key, base_url=base_url)
        model_name = model or os.getenv("MINIMAX_JUDGE_MODEL", DEFAULT_JUDGE_MODEL)
        answer_text = str(answer)

        async def judge_one(criterion: _Criterion) -> _Verdict:
            response = await client.chat.completions.create(
                model=model_name,
                max_tokens=512,
                temperature=0,
                messages=[
                    {"role": "system", "content": JUDGE_SYSTEM_PROMPT},
                    {
                        "role": "user",
                        "content": _criterion_prompt(criterion, answer_text, question),
                    },
                ],
            )
            met, reason = _parse_verdict(response.choices[0].message.content or "")
            return _Verdict(criterion=criterion, met=met, reason=reason)

        verdicts = list(await asyncio.gather(*(judge_one(item) for item in parsed)))
        return _aggregate(verdicts), {
            "criteria": {
                verdict.criterion.requirement[:80]: {
                    "verdict": "MET" if verdict.met else "UNMET",
                    "reason": verdict.reason,
                    "weight": verdict.criterion.weight,
                }
                for verdict in verdicts
            },
            "model": model_name,
            "base_url": str(client.base_url),
        }


@env.template(id="llm-judge")
async def llm_judge(
    prompt: str,
    judge: dict[str, Any],
    model: str = DEFAULT_JUDGE_MODEL,
    base_url: str | None = None,
):
    answer = yield prompt
    subscore = await MiniMaxJudgeGrader.grade(
        weight=1.0,
        name=str(judge.get("name", "llm-judge")),
        answer=answer or "",
        criteria=_criteria_from_judge(judge),
        question=_judge_question(prompt, judge),
        model=model,
        base_url=base_url,
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


def _parse_criteria(criteria: list[str | tuple[str, float]] | None) -> list[_Criterion]:
    parsed: list[_Criterion] = []
    for item in criteria or []:
        if isinstance(item, tuple):
            requirement, weight = item
            parsed.append(_Criterion(str(requirement), float(weight)))
        else:
            parsed.append(_Criterion(str(item), 1.0))
    return parsed


def _criterion_prompt(criterion: _Criterion, answer: str, question: str) -> str:
    criterion_type = "negative" if criterion.weight < 0 else "positive"
    return (
        f"<criterion_type>\n{criterion_type}\n</criterion_type>\n\n"
        f"<criterion>\n{criterion.requirement}\n</criterion>\n\n"
        f"<question>\n{question}\n</question>\n\n"
        f"<response>\n{answer}\n</response>"
    )


def _parse_verdict(content: str) -> tuple[bool, str]:
    text = content.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()
    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end > start:
        try:
            data = json.loads(text[start : end + 1])
            return str(data.get("criterion_status", "")).upper() == "MET", str(
                data.get("explanation", "")
            )
        except (TypeError, ValueError):
            pass

    upper = text.upper()
    return "UNMET" not in upper and "MET" in upper, text[:200]


def _aggregate(verdicts: list[_Verdict]) -> float:
    positive_weight = sum(max(0.0, verdict.criterion.weight) for verdict in verdicts)
    negative_weight = sum(
        abs(verdict.criterion.weight) for verdict in verdicts if verdict.criterion.weight < 0
    )
    weighted_sum = sum(
        (1.0 if verdict.met else 0.0) * verdict.criterion.weight for verdict in verdicts
    )

    if positive_weight > 0:
        return max(0.0, min(1.0, weighted_sum / positive_weight))
    if negative_weight > 0:
        return max(0.0, min(1.0, 1.0 + weighted_sum / negative_weight))
    return 0.0


def _minimax_client(
    api_key: str | None = None,
    base_url: str | None = None,
):
    from openai import AsyncOpenAI

    _load_local_env()
    resolved_api_key = api_key or os.getenv("MINIMAX_API_KEY")
    if not resolved_api_key:
        raise RuntimeError("MINIMAX_API_KEY is required for MiniMax judge calls")

    return AsyncOpenAI(
        api_key=resolved_api_key,
        base_url=base_url or os.getenv("MINIMAX_BASE_URL", DEFAULT_MINIMAX_BASE_URL),
    )


def _load_local_env() -> None:
    for path in (Path.cwd() / ".env", Path(__file__).with_name(".env")):
        if not path.exists():
            continue
        for line in path.read_text(encoding="utf-8").splitlines():
            stripped = line.strip()
            if not stripped or stripped.startswith("#") or "=" not in stripped:
                continue
            key, value = stripped.split("=", 1)
            os.environ.setdefault(key.strip(), value.strip().strip("'\""))


def _judge_question(prompt: str, judge: dict[str, Any]) -> str:
    return (
        f"{prompt}\n\n"
        "Judge using this JSON scoring specification:\n"
        f"{json.dumps(judge, indent=2, sort_keys=True)}"
    )
