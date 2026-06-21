"""Task aggregator for HUD.

Do not add concrete tasks here.
"""

from mousecad_env import env  # noqa: F401

from cad_description_tasks import tasks as cad_description_tasks
from cad_edit_tasks import tasks as cad_edit_tasks

tasks = [
    *cad_edit_tasks,
    *cad_description_tasks,
]
