"""CAD edit tasks.

Own this file when adding tasks where the agent must change the CAD model.
Examples include "make a 10x10x10 cm cube", "add four holes", or "cut a slot".
"""

from env import cad_edit


def edit_task(
    slug: str,
    input_text: str,
    ideal_output: str | None = None,
    required_substrings: list[str] | None = None,
):
    """Create one ``cad-edit`` task row."""
    task = cad_edit(
        input_text=input_text,
        ideal_output=ideal_output,
        required_substrings=required_substrings,
    )
    task.slug = slug
    return task


tasks = [
    # Add CAD-edit task rows here.
]
