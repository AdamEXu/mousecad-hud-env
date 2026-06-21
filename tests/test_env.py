from cad_description_tasks import cad_description, task as description_task
from cad_edit_tasks import cad_edit, task as edit_task
from tasks import tasks


class TestCadEdit:
    async def test_exact_match(self):
        gen = cad_edit.func(prompt="prompt", expected_output="answer")
        assert await gen.asend(None) == "prompt"
        assert await gen.asend("answer") == 1.0

    async def test_mismatch(self):
        gen = cad_edit.func(prompt="prompt", expected_output="answer")
        await gen.asend(None)
        assert await gen.asend("wrong") == 0.0

    def test_helper_sets_slug(self):
        row = edit_task("edit-1", "prompt", "answer")
        assert row.slug == "edit-1"


class TestCadDescription:
    async def test_exact_match(self):
        gen = cad_description.func(prompt="prompt", expected_output="answer")
        assert await gen.asend(None) == "prompt"
        assert await gen.asend("answer") == 1.0

    async def test_mismatch(self):
        gen = cad_description.func(prompt="prompt", expected_output="answer")
        await gen.asend(None)
        assert await gen.asend("wrong") == 0.0

    def test_helper_sets_slug(self):
        row = description_task("description-1", "prompt", "answer")
        assert row.slug == "description-1"


def test_no_default_tasks():
    assert tasks == []
