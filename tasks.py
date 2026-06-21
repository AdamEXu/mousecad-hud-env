"""Task aggregator for HUD.

Do not add concrete tasks here.
"""

from mousecad_env import env  # noqa: F401

from cad_description_tasks import tasks as _cad_description_tasks
from cad_edit_tasks import tasks as _cad_edit_tasks

tasks = [
    *_cad_edit_tasks,
    *_cad_description_tasks,
]
