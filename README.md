# MouseCAD HUD Environment

Deterministic RL environment for compact CAD-code models. The model receives a
MouseCAD edit request and must emit exactly one `predict_cad_template` tool call
containing executable Python CAD DSL code.

Reward gates:

1. If the output is not exactly the requested tool-call wrapper, reward is `0`.
2. If the Python template is unsafe, uses anything outside the CAD DSL, or raises
   at execution time, reward is `0`.
3. If it executes, the grader scores CAD procedure structure and the simulated
   geometry against the task spec.

File split:

- `env.py`: HUD entry point only.
- `mousecad_env.py`: shared `env` object only.
- `cad_dsl.py`: small executable/recordable CAD DSL stub.
- `cad_reward.py`: deterministic wrapper, execution, procedure, and geometry scorer.
- `prompts.py`: shared task prompt text.
- `cad_edit_tasks.py`: five hand-written CAD template challenges.
- `cad_description_tasks.py`: empty placeholder for compatibility.
- `tasks.py`: combines both task lists.

Current challenges:

- `make-cube-5cm`
- `make-equilateral-triangle-prism-5cm`
- `make-cube-5cm-with-top-triangle-2cm`
- `make-cylinder-3cm-diameter-5cm-tall`
- `make-rectangular-prism-5cm-3cm-2cm`

Run tests:

```bash
uv run pytest tests/
```
