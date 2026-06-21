"""MouseCAD HUD environment.

The environment exposes two task templates:

* ``cad-edit`` asks the agent to produce a CAD edit tool call.
* ``cad-describe`` asks the agent to explain the current CAD context.

Concrete task rows live in ``cad_edit_tasks.py`` and
``cad_description_tasks.py`` so collaborators can work on separate files.
"""

from __future__ import annotations

from collections.abc import Sequence

from hud import Environment

env = Environment(name="mousecad")


def _normalize_text(text: str | None) -> str:
    """Normalize generated text for deterministic task scoring."""
    if not text:
        return ""
    return "\n".join(line.rstrip() for line in text.strip().splitlines()).strip()


def _contains_all(answer: str, required_phrases: Sequence[str]) -> bool:
    haystack = answer.lower()
    return all(phrase.lower() in haystack for phrase in required_phrases)


def _score_answer(
    answer: str | None,
    ideal_answer: str | None = None,
    required_phrases: Sequence[str] | None = None,
) -> float:
    normalized = _normalize_text(answer)
    if not normalized:
        return 0.0

    if ideal_answer is not None:
        return 1.0 if normalized == _normalize_text(ideal_answer) else 0.0

    if required_phrases:
        return 1.0 if _contains_all(normalized, required_phrases) else 0.0

    return 0.0


@env.template(id="cad-edit")
async def cad_edit(
    input_text: str,
    ideal_output: str | None = None,
    required_substrings: list[str] | None = None,
):
    """Ask the agent to apply a CAD edit.

    ``input_text`` should usually be the XML-ish MouseCAD prompt containing
    ``<task_type>``, ``<user_request>``, ``<selection>``, ``<history>``, and
    ``<template>``. Score with ``ideal_output`` for strict tool-call matching,
    or with ``required_substrings`` while a task is still being drafted.
    """
    answer = yield input_text.strip()
    yield _score_answer(answer, ideal_output, required_substrings)


@env.template(id="cad-describe")
async def cad_describe(
    cad_context: str,
    question: str = "What do you see?",
    ideal_answer: str | None = None,
    required_phrases: list[str] | None = None,
):
    """Ask the agent to describe or answer questions about a CAD context."""
    prompt = f"{cad_context.strip()}\n\n<question>\n{question.strip()}\n</question>"
    answer = yield prompt
    yield _score_answer(answer, ideal_answer, required_phrases)


if __name__ == "__main__":
    import asyncio

    async def _smoke() -> None:
        gen = cad_describe.func(
            cad_context="A cube with side length 10 cm.",
            ideal_answer="I see a cube with side length 10 cm.",
        )
        print(await gen.asend(None))
        print("reward:", await gen.asend("I see a cube with side length 10 cm."))

    asyncio.run(_smoke())
