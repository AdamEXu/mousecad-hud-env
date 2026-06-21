# MouseCAD Training API RL

This directory is for the Fireworks Training API path requested by the
`qwen3_5 is not supported by legacy CreateReinforcementFineTuningJob` error.
It runs rewards directly in the Training API rollout loop.

The intended flow is:

1. Build prompt rows from the MouseCAD reward dataset.
2. Run a Fireworks Training API cookbook RL loop.
3. Compute reward locally with `fireworks_rft.cad_reward.grade_answer`.
4. Promote the final checkpoint to a Fireworks model.

The legacy Fireworks RFT wizard uses `CreateReinforcementFineTuningJob` and
fails for the Qwen3.6 model family. The Training API path is the replacement.

## Setup

Install the Fireworks Training API packages in the repo venv:

```bash
uv sync --group dev --group training --prerelease allow
```

The `training` dependency group pulls the Fireworks Training SDK and the
official cookbook training package from GitHub.

## Validate Locally

```bash
uv run --group training --prerelease allow python -m training_sdk_rl.train_mousecad \
  --dataset-path fireworks_rft/dataset.jsonl \
  --max-rows 5 \
  --dry-run
```

## Launch Training API RL

```bash
export FIREWORKS_API_KEY='...'
uv run --group training --prerelease allow python -m training_sdk_rl.train_mousecad \
  --dataset-path fireworks_rft/dataset.deepcad.eval.sample.jsonl \
  --base-model accounts/tst-k2klvfh7t1ge/models/mc-predict-qwen36-27b-lora-120k-turbo-20260621002157 \
  --tokenizer-model Qwen/Qwen3.6-27B \
  --training-shape-id accounts/fireworks/trainingShapes/qwen3p6-27b-128k-lora \
  --max-rows 128 \
  --completions-per-prompt 4 \
  --prompt-groups-per-step 4 \
  --lora-rank 8
```

For a larger run, build a bigger eval-protocol dataset from DeepCAD-derived
JSONL first:

```bash
uv run python scripts/build_deepcad_rft_dataset.py \
  --format eval-protocol \
  --max-rows-per-source 1000 \
  --output fireworks_rft/dataset.deepcad.eval.2k.jsonl
```

Measurement errors are heavily punished by the reward function: scale fields
such as `distance`, `radius`, `start`, `end`, `corner1`, and `corner2` carry
extra weight, and scale mismatches cap the relevant score.
