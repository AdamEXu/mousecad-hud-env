# MouseCAD HUD Environment

This repo is a HUD v6 environment scaffold for two separate MouseCAD task
tracks:

- `cad-edit`: the agent must change the CAD model by returning an
  `apply_cad_edit` tool call.
- `cad-describe`: the agent must explain or answer questions about the CAD
  context.

The default count-letter and calculator tasks have been removed. Each track owns
its own template, helper, and concrete task rows so two people can work without
touching the same task file.

| File | Role |
|------|------|
| `env.py` | Tiny HUD serve entry point; imports task modules for registration. |
| `mousecad_env.py` | Shared HUD `env` object and generic scoring helpers. |
| `cad_edit_tasks.py` | CAD-edit template, helper, and task rows. |
| `cad_description_tasks.py` | CAD-description template, helper, and task rows. |
| `tasks.py` | Thin HUD aggregator that combines both task lists. |
| `tests/` | Offline tests for templates, scoring, and task-module wiring. |

## Setup

```bash
uv sync
hud set HUD_API_KEY=your-key-here
```

## Add CAD Edit Tasks

Put edit tasks in `cad_edit_tasks.py`. If the edit prompt or reward logic needs
to change, change the `cad_edit` template in this same file.

```python
tasks = [
    edit_task(
        slug="edit-raised-boss",
        input_text="""<task_type>
apply_template_to_selection
</task_type>

...""",
        ideal_output="""<tool_call>
<function=apply_cad_edit>
<parameter=python_script>
...
</parameter>
</function>
</tool_call>""",
    ),
]
```

Use `ideal_output` for strict tool-call matching. While drafting a task, you can
use `required_substrings=["apply_cad_edit", "extrude"]` instead.

## Add CAD Description Tasks

Put description tasks in `cad_description_tasks.py`. If the description prompt
or reward logic needs to change, change the `cad_describe` template in this same
file.

```python
tasks = [
    description_task(
        slug="describe-cube-10cm",
        cad_context="""<history>
CUBE side=10cm
</history>""",
        question="What do you see?",
        ideal_answer="I see a cube with side length 10 cm.",
    ),
]
```

Use `ideal_answer` for strict matching, or `required_phrases=["cube", "10 cm"]`
for early draft tasks.

## Run Locally

```bash
uv run pytest tests/
uv run python env.py
hud eval tasks.py claude --task-ids <slug> --group 3
```

## Deploy And Sync

```bash
hud deploy .
hud sync tasks mousecad
hud eval mousecad --remote --full
```

After the first deploy, editing only task rows normally needs `hud sync tasks`.
Redeploy when a template, shared scoring helper, dependency, or Dockerfile
changes.
