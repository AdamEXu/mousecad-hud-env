from cad_description_tasks import tasks as description_tasks
from cad_edit_tasks import tasks as edit_tasks
from mousecad_env import env
from tasks import tasks


def test_env_exists():
    assert env.name == "mousecad"


def test_no_default_tasks():
    assert edit_tasks == []
    assert description_tasks == []
    assert tasks == []
