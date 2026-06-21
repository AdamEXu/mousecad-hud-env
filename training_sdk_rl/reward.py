from __future__ import annotations

from typing import Any

from fireworks_rft.cad_reward import Grade, grade_answer


def extract_spec(row: dict[str, Any]) -> dict[str, Any] | None:
    """Return the CAD grading spec from a Training SDK dataset row."""

    ground_truth = row.get("ground_truth")
    if isinstance(ground_truth, dict):
        return ground_truth

    metadata = row.get("input_metadata")
    if isinstance(metadata, dict):
        dataset_info = metadata.get("dataset_info")
        if isinstance(dataset_info, dict):
            spec = dataset_info.get("spec")
            if isinstance(spec, dict):
                return spec

    spec = row.get("spec")
    if isinstance(spec, dict):
        return spec

    return None


def grade_completion(completion: str, row: dict[str, Any]) -> Grade:
    """Score a model completion with the deterministic CAD verifier."""

    spec = extract_spec(row)
    if spec is None:
        return Grade(0.0, {"stage": "dataset", "error": "row is missing ground_truth/spec"})
    return grade_answer(completion, spec)

