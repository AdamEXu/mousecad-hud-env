from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from fireworks.training.sdk.deployment import DeploymentSampler
from training.utils.rl.rollout import (
    MessageTrajectoryAssembler,
    RolloutRun,
    RolloutSample,
    TITOTokenizer,
)

from training_sdk_rl.reward import grade_completion

if TYPE_CHECKING:
    from training.recipes.async_rl_loop import RolloutFn, RolloutSetup


logger = logging.getLogger(__name__)


def make_rollout_fn(setup: "RolloutSetup") -> "RolloutFn":
    """Build a one-turn CAD-template rollout function for Training API RL."""

    sampler = DeploymentSampler(
        inference_url=setup.inference_base_url,
        model=setup.model,
        api_key=setup.api_key,
        tokenizer=setup.tokenizer,
    )
    sample_kwargs = dict(setup.sample_kwargs)
    tokenizer = setup.tokenizer

    async def rollout_fn(sample_prompt: dict) -> RolloutRun | None:
        messages = list(sample_prompt.get("messages") or [])
        if not messages:
            logger.warning("dropping row without messages")
            return None

        assembler = MessageTrajectoryAssembler(TITOTokenizer(tokenizer))
        prompt_tokens = assembler.prepare_next_input(messages)
        completions = await sampler.sample_with_prompt_tokens(
            prompt_tokens,
            n=1,
            **sample_kwargs,
        )
        if not completions:
            return None

        completion = completions[0]
        prompt_len = int(completion.prompt_len)
        output_tokens = list(completion.full_tokens[prompt_len:])
        output_logprobs = list(completion.inference_logprobs or [])
        if (
            getattr(completion, "logprobs_echoed", False)
            and len(output_logprobs) == len(completion.full_tokens)
        ):
            output_logprobs = output_logprobs[prompt_len:]
        if not output_tokens or len(output_logprobs) != len(output_tokens):
            logger.warning(
                "dropping row with invalid token/logprob shape tokens=%d logprobs=%d",
                len(output_tokens),
                len(output_logprobs),
            )
            return None

        assistant_text = getattr(completion, "text", "") or tokenizer.decode(output_tokens)
        assistant_message = {"role": "assistant", "content": assistant_text}
        assembler.add_assistant_response(
            request_messages=messages,
            assistant_message=assistant_message,
            prompt_token_ids=prompt_tokens,
            completion_token_ids=output_tokens,
            completion_logprobs=output_logprobs,
            finish_reason=getattr(completion, "finish_reason", "stop"),
        )

        grade = grade_completion(assistant_text, sample_prompt)
        tokens, logprobs, loss_mask = assembler.trajectory.to_flat()
        sample = RolloutSample(
            tokens=tokens,
            logprobs=logprobs,
            loss_mask=loss_mask,
            reward=float(grade.reward),
            text=assistant_text,
            finish_reason=getattr(completion, "finish_reason", "stop"),
        )
        return RolloutRun(
            segments=[sample],
            metadata={
                "reward": grade.reward,
                "reward_details": grade.details,
                "row_id": _row_id(sample_prompt),
            },
        )

    return rollout_fn


def _row_id(row: dict) -> str | None:
    metadata = row.get("input_metadata")
    if isinstance(metadata, dict) and metadata.get("row_id"):
        return str(metadata["row_id"])
    if row.get("id"):
        return str(row["id"])
    return None

