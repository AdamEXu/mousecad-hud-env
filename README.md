# MouseCAD HUD Environment

Bare split:

- `env.py`: HUD entry point only.
- `mousecad_env.py`: shared `env` object only.
- `llm_judge.py`: shared LLM-judge template.
- `cad_edit_tasks.py`: hand-written edit benchmarks.
- `cad_description_tasks.py`: hand-written description benchmarks.
- `tasks.py`: combines both task lists.

Use `llm_judge` when a benchmark should be scored from a JSON judge spec:

```python
from llm_judge import llm_judge

_my_benchmark = llm_judge(
    prompt="...",
    judge={
        "name": "...",
        "criteria": [
            {"requirement": "...", "weight": 1.0},
        ],
    },
)
_my_benchmark.slug = "my-benchmark"

tasks = [_my_benchmark]
```

For fully custom scoring, define a one-off `@env.template` directly in the edit
or description task file.

MiniMax judge config:

```bash
MINIMAX_API_KEY=...
MINIMAX_BASE_URL=https://api.minimax.io/v1
MINIMAX_JUDGE_MODEL=MiniMax-M3
```

Only `MINIMAX_API_KEY` is required. The base URL and model have defaults.

Run tests:

```bash
uv run pytest tests/
```
