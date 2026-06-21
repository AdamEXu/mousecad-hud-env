"""Task aggregator for HUD.

Add CAD edit tasks in ``cad_edit_tasks.py`` and CAD description tasks in
``cad_description_tasks.py``. This file should stay small and rarely change,
which keeps collaborators out of each other's task files.
"""

# env is re-exported so `hud eval tasks.py` can resolve the Environment.
from mousecad_env import env  # noqa: F401

from cad_description_tasks import tasks as cad_description_tasks
from cad_edit_tasks import tasks as cad_edit_tasks

tasks = [
    *cad_edit_tasks,
    *cad_description_tasks,
]
