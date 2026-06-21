#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import logging
import os
import sys
import time
from pathlib import Path
from typing import Any, Iterator

from training.recipes.async_rl_loop import Config, main
from training.utils import DeployConfig, TrainerConfig, WandBConfig

from training_sdk_rl.reward import extract_spec, grade_completion
from training_sdk_rl.rollout import make_rollout_fn


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DATASET = ROOT / "fireworks_rft" / "dataset.jsonl"
DEFAULT_MODEL = "accounts/tst-k2klvfh7t1ge/models/mc-predict-qwen36-27b-lora-120k-turbo-20260621002157"
DEFAULT_TOKENIZER = "Qwen/Qwen3.6-27B"
DEFAULT_TRAINING_SHAPE = "accounts/fireworks/trainingShapes/qwen3p6-27b-128k-lora"
DEFAULT_OUTPUT_MODEL_PREFIX = "accounts/tst-k2klvfh7t1ge/models/mc-predict-qwen36-cad-rft-sdk"


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)


def iter_rows(path: Path, max_rows: int | None) -> Iterator[dict[str, Any]]:
    count = 0
    with path.open() as file:
        for line in file:
            line = line.strip()
            if not line:
                continue
            yield json.loads(line)
            count += 1
            if max_rows is not None and count >= max_rows:
                return


def validate_rows(rows: list[dict[str, Any]]) -> None:
    if not rows:
        raise ValueError("dataset produced zero rows")

    missing_messages = 0
    missing_specs = 0
    perfect_references = 0
    for row in rows:
        if not row.get("messages"):
            missing_messages += 1
        spec = extract_spec(row)
        if spec is None:
            missing_specs += 1
            continue
        reference = spec.get("reference_template")
        if isinstance(reference, str) and reference.strip():
            answer = (
                "<tool_call>\n"
                "<function=predict_cad_template>\n"
                "<parameter=template>\n"
                f"{reference.strip()}\n"
                "</parameter>\n"
                "</function>\n"
                "</tool_call>"
            )
            if grade_completion(answer, row).reward >= 0.99:
                perfect_references += 1

    if missing_messages:
        raise ValueError(f"{missing_messages} rows are missing messages")
    if missing_specs:
        raise ValueError(f"{missing_specs} rows are missing CAD grading specs")

    logger.info(
        "validated %d rows; %d rows contain self-scoring reference templates",
        len(rows),
        perfect_references,
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="MouseCAD Fireworks Training API RL runner")
    parser.add_argument("--dataset-path", default=str(DEFAULT_DATASET))
    parser.add_argument("--base-model", default=DEFAULT_MODEL)
    parser.add_argument("--tokenizer-model", default=DEFAULT_TOKENIZER)
    parser.add_argument("--training-shape-id", default=DEFAULT_TRAINING_SHAPE)
    parser.add_argument("--output-model-id", default=None)
    parser.add_argument("--max-rows", type=int, default=128)
    parser.add_argument("--epochs", type=int, default=1)
    parser.add_argument("--completions-per-prompt", type=int, default=4)
    parser.add_argument("--prompt-groups-per-step", type=int, default=4)
    parser.add_argument("--max-completion-tokens", type=int, default=1536)
    parser.add_argument("--temperature", type=float, default=0.9)
    parser.add_argument("--learning-rate", type=float, default=1.0e-5)
    parser.add_argument("--kl-beta", type=float, default=0.0)
    parser.add_argument("--lora-rank", type=int, default=8)
    parser.add_argument("--max-concurrency-rollout-sample", type=int, default=16)
    parser.add_argument("--replica-count", type=int, default=1)
    parser.add_argument("--log-path", default="./mousecad_training_sdk_rl_logs")
    parser.add_argument("--wandb-entity", default=os.environ.get("WANDB_ENTITY", ""))
    parser.add_argument("--wandb-project", default=os.environ.get("WANDB_PROJECT", "mousecad-cad-rl"))
    parser.add_argument("--wandb-run-name", default=None)
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Validate imports, rows, reward specs, and config without creating remote Fireworks resources.",
    )
    return parser.parse_args()


def run() -> None:
    args = parse_args()
    dataset_path = Path(args.dataset_path)
    if not dataset_path.exists():
        raise FileNotFoundError(dataset_path)

    rows = list(iter_rows(dataset_path, args.max_rows))
    validate_rows(rows)

    output_model_id = args.output_model_id
    if not output_model_id:
        output_model_id = f"{DEFAULT_OUTPUT_MODEL_PREFIX}-{int(time.time())}"

    cfg = Config(
        log_path=args.log_path,
        base_model=args.base_model,
        learning_rate=args.learning_rate,
        kl_beta=args.kl_beta,
        completions_per_prompt=args.completions_per_prompt,
        max_completion_tokens=args.max_completion_tokens,
        temperature=args.temperature,
        epochs=args.epochs,
        max_rows=args.max_rows,
        lora_rank=args.lora_rank,
        prompt_groups_per_step=args.prompt_groups_per_step,
        max_concurrency_rollout_sample=args.max_concurrency_rollout_sample,
        output_model_id=output_model_id,
        trainer=TrainerConfig(training_shape_id=args.training_shape_id),
        deployment=DeployConfig(
            tokenizer_model=args.tokenizer_model,
            replica_count=args.replica_count,
        ),
        wandb=WandBConfig(
            entity=args.wandb_entity,
            project=args.wandb_project,
            run_name=args.wandb_run_name or f"mousecad-cad-rl-{int(time.time()) % 100000}",
        ),
    )

    logger.info("base_model=%s", cfg.base_model)
    logger.info("training_shape_id=%s", args.training_shape_id)
    logger.info("output_model_id=%s", output_model_id)
    if args.dry_run:
        logger.info("dry run complete; no Fireworks trainer/deployment was created")
        return

    if not os.environ.get("FIREWORKS_API_KEY"):
        raise RuntimeError("FIREWORKS_API_KEY must be set to launch Training API RL")

    main(
        cfg,
        rollout_fn_factory=make_rollout_fn,
        rows=rows,
    )


if __name__ == "__main__":
    try:
        run()
    except Exception as exc:
        print(f"error: {exc}", file=sys.stderr)
        raise

