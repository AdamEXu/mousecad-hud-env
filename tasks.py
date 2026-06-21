"""Task aggregator for MouseCAD direct Fireworks training/evaluation."""

from cad_description_tasks import tasks as _cad_description_tasks
from cad_edit_tasks import tasks as _cad_edit_tasks

tasks = [
    *_cad_edit_tasks,
    *_cad_description_tasks,
]
