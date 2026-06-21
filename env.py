"""HUD serve entry point.

Track-specific templates and task rows live in ``cad_edit_tasks.py`` and
``cad_description_tasks.py``. Importing those modules registers their templates
on the shared ``env`` object.
"""

from mousecad_env import env

# Imported for template registration side effects.
from cad_description_tasks import cad_describe  # noqa: F401
from cad_edit_tasks import cad_edit  # noqa: F401


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
