from mousecad_env import env


@env.template(id="cad-edit")
async def cad_edit(prompt: str, expected_output: str):
    answer = yield prompt
    yield 1.0 if (answer or "").strip() == expected_output.strip() else 0.0


def task(slug: str, prompt: str, expected_output: str):
    row = cad_edit(prompt=prompt, expected_output=expected_output)
    row.slug = slug
    return row


tasks = []
