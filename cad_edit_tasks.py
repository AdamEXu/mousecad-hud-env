"""CAD edit tasks.

Own this file when adding tasks where the agent must change the CAD model.
Examples include "make a 10x10x10 cm cube", "add four holes", or "cut a slot".
"""

from mousecad_env import env, score_answer


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
    yield score_answer(answer, ideal_output, required_substrings)


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
