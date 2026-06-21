"""Tests for the MouseCAD HUD environment templates and task modules."""

from cad_description_tasks import description_task, tasks as cad_description_tasks
from cad_edit_tasks import edit_task, tasks as cad_edit_tasks
from env import _score_answer, cad_describe, cad_edit
from tasks import tasks


class TestScoring:
    def test_exact_answer_match(self):
        assert _score_answer("answer\n", "answer") == 1.0

    def test_exact_answer_mismatch(self):
        assert _score_answer("answer", "different") == 0.0

    def test_required_phrases_are_case_insensitive(self):
        assert _score_answer(
            "I see a 10 cm cube.",
            required_phrases=["10 CM", "cube"],
        ) == 1.0

    def test_empty_answer_is_wrong(self):
        assert _score_answer("", required_phrases=["cube"]) == 0.0


class TestCadEditTemplate:
    async def test_prompt_is_raw_mousecad_input(self):
        gen = cad_edit.func(
            input_text="<task_type>\napply_template_to_selection\n</task_type>",
            ideal_output="<tool_call>ok</tool_call>",
        )
        prompt = await gen.asend(None)
        assert prompt == "<task_type>\napply_template_to_selection\n</task_type>"

    async def test_scores_exact_tool_call(self):
        ideal = "<tool_call>\n<function=apply_cad_edit />\n</tool_call>"
        gen = cad_edit.func(input_text="Make a cube.", ideal_output=ideal)
        await gen.asend(None)
        reward = await gen.asend(ideal)
        assert reward == 1.0

    async def test_rejects_wrong_tool_call(self):
        gen = cad_edit.func(
            input_text="Make a cube.",
            ideal_output="<tool_call>cube</tool_call>",
        )
        await gen.asend(None)
        reward = await gen.asend("<tool_call>sphere</tool_call>")
        assert reward == 0.0

    async def test_can_score_draft_tasks_by_required_substrings(self):
        gen = cad_edit.func(
            input_text="Make a cube.",
            required_substrings=["apply_cad_edit", "extrude"],
        )
        await gen.asend(None)
        reward = await gen.asend("<function=apply_cad_edit>extrude</function>")
        assert reward == 1.0


class TestCadDescribeTemplate:
    async def test_prompt_contains_context_and_question(self):
        gen = cad_describe.func(
            cad_context="<history>\nCUBE side=10cm\n</history>",
            question="What do you see?",
            ideal_answer="I see a cube with side length 10 cm.",
        )
        prompt = await gen.asend(None)
        assert "<history>\nCUBE side=10cm\n</history>" in prompt
        assert "<question>\nWhat do you see?\n</question>" in prompt

    async def test_scores_exact_description(self):
        gen = cad_describe.func(
            cad_context="CUBE side=10cm",
            ideal_answer="I see a cube with side length 10 cm.",
        )
        await gen.asend(None)
        reward = await gen.asend("I see a cube with side length 10 cm.")
        assert reward == 1.0

    async def test_can_score_description_by_required_phrases(self):
        gen = cad_describe.func(
            cad_context="CUBE side=10cm",
            required_phrases=["cube", "10 cm"],
        )
        await gen.asend(None)
        reward = await gen.asend("The model is a cube with side length 10 cm.")
        assert reward == 1.0


class TestTaskModules:
    def test_default_task_lists_are_empty(self):
        assert cad_edit_tasks == []
        assert cad_description_tasks == []
        assert tasks == []

    def test_edit_task_helper_sets_slug(self):
        task = edit_task(
            slug="edit-make-cube",
            input_text="Make a cube.",
            ideal_output="<tool_call>cube</tool_call>",
        )
        assert task.slug == "edit-make-cube"

    def test_description_task_helper_sets_slug(self):
        task = description_task(
            slug="describe-cube",
            cad_context="CUBE side=10cm",
            ideal_answer="I see a cube with side length 10 cm.",
        )
        assert task.slug == "describe-cube"
