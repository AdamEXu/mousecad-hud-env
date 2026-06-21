# MouseCAD HUD Environment

Bare split:

- `env.py`: HUD entry point only.
- `mousecad_env.py`: shared `env` object only.
- `cad_edit_tasks.py`: edit template and edit task rows.
- `cad_description_tasks.py`: description template and description task rows.
- `tasks.py`: combines both task lists.

Add concrete rows only in one of the two task files:

```python
tasks = [
    task(
        slug="...",
        prompt="...",
        expected_output="...",
    ),
]
```

Run tests:

```bash
uv run pytest tests/
```
