import json
import os
from pathlib import Path
from typing import Any

from eval_protocol import (
    EvaluateResult,
    EvaluationRow,
    MetricResult,
    SingleTurnRolloutProcessor,
    evaluation_test,
)

from cad_reward import grade_answer


WARM_START_MODEL = "accounts/tst-k2klvfh7t1ge/models/mc-predict-qwen36-27b-lora-120k-turbo-20260621002157"
ROLLOUT_MODEL = WARM_START_MODEL
DATASET_PATH = Path(os.environ.get("MOUSECAD_RFT_DATASET", Path(__file__).with_name("dataset.jsonl")))


def _content_to_text(content: Any) -> str:
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        chunks: list[str] = []
        for item in content:
            if isinstance(item, dict) and item.get("type") == "text":
                chunks.append(str(item.get("text", "")))
        return "\n".join(chunks)
    return "" if content is None else str(content)


@evaluation_test(
    input_dataset=[str(DATASET_PATH)],
    completion_params=[
        {
            "model": f"fireworks_ai/{ROLLOUT_MODEL}",
            "temperature": 0.8,
            "top_p": 0.95,
            "max_tokens": 2048,
        }
    ],
    rollout_processor=SingleTurnRolloutProcessor(),
    aggregation_method="mean",
    passed_threshold=0.8,
    num_runs=1,
    max_concurrent_rollouts=4,
    max_concurrent_evaluations=16,
    disable_browser_open=True,
    mode="pointwise",
)
def test_mousecad_cad_template_reward(row: EvaluationRow) -> EvaluationRow:
    assistant_message = row.last_assistant_message()
    if assistant_message is None:
        row.evaluation_result = EvaluateResult(
            score=0.0,
            reason="No assistant response was produced.",
            is_score_valid=False,
        )
        return row

    answer = _content_to_text(assistant_message.content)
    dataset_info = row.input_metadata.dataset_info or {}
    spec = dataset_info.get("spec") or row.ground_truth
    if not isinstance(spec, dict):
        row.evaluation_result = EvaluateResult(
            score=0.0,
            reason="Dataset row does not contain a CAD reward spec.",
            is_score_valid=False,
        )
        return row

    result = grade_answer(answer, spec)
    details_json = json.dumps(result.details, sort_keys=True)
    row.evaluation_result = EvaluateResult(
        score=result.reward,
        reason=details_json[:4000],
        is_score_valid=True,
        metrics={
            "cad_reward": MetricResult(
                score=result.reward,
                is_score_valid=True,
                reason=result.details.get("stage", "scored"),
                data=result.details,
            )
        },
    )
    return row
