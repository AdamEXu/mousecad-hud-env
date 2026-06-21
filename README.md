# MouseCAD HUD Environment

Bare split:

- `env.py`: HUD entry point only.
- `mousecad_env.py`: shared `env` object only.
- `cad_edit_tasks.py`: hand-written edit benchmarks.
- `cad_description_tasks.py`: hand-written description benchmarks.
- `tasks.py`: combines both task lists.

Add every benchmark by hand in one of the two task files. Define its own
`@env.template`, prompt, scoring function, slug, and task list entry there.

```python
@env.template(id="my-benchmark")
async def my_benchmark():
    answer = yield "..."
    yield ...


_my_benchmark = my_benchmark()
_my_benchmark.slug = "my-benchmark"

tasks = [_my_benchmark]
```

Run tests:

```bash
uv run pytest tests/
```
