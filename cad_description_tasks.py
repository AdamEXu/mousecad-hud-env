"""CAD description tasks.

Own this file when adding tasks where the agent must explain the CAD context.
Examples include "what do you see?", dimension questions, feature counts, or
selection-specific inspection questions.
"""

from env import cad_describe


def description_task(
    slug: str,
    cad_context: str,
    question: str = "What do you see?",
    ideal_answer: str | None = None,
    required_phrases: list[str] | None = None,
):
    """Create one ``cad-describe`` task row."""
    task = cad_describe(
        cad_context=cad_context,
        question=question,
        ideal_answer=ideal_answer,
        required_phrases=required_phrases,
    )
    task.slug = slug
    return task


tasks = [
    # Add CAD-description task rows here.
]
