"""Shared MouseCAD HUD environment object and scoring helpers."""

from __future__ import annotations

from collections.abc import Sequence

from hud import Environment

env = Environment(name="mousecad")


def normalize_text(text: str | None) -> str:
    """Normalize generated text for deterministic task scoring."""
    if not text:
        return ""
    return "\n".join(line.rstrip() for line in text.strip().splitlines()).strip()


def contains_all(answer: str, required_phrases: Sequence[str]) -> bool:
    haystack = answer.lower()
    return all(phrase.lower() in haystack for phrase in required_phrases)


def score_answer(
    answer: str | None,
    ideal_answer: str | None = None,
    required_phrases: Sequence[str] | None = None,
) -> float:
    normalized = normalize_text(answer)
    if not normalized:
        return 0.0

    if ideal_answer is not None:
        return 1.0 if normalized == normalize_text(ideal_answer) else 0.0

    if required_phrases:
        return 1.0 if contains_all(normalized, required_phrases) else 0.0

    return 0.0
