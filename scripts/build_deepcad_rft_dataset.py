from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from cad_reward import grade_answer
from prompts import build_prompt


DEFAULT_TESTING_ROOT = Path("/Users/godbrigero/Documents/MouseCADDataFilter/dataset/testing_dataset")
DEFAULT_OUTPUT = Path("fireworks_rft/dataset.deepcad.jsonl")
DEFAULT_SOURCES = (
    "insertion_model/insertion_examples_with_user_requests_123k.jsonl",
    "autocomplete_model/autocomplete_examples.jsonl",
)


def wrap_template(template: str) -> str:
    return (
        "<tool_call>\n"
        "<function=predict_cad_template>\n"
        "<parameter=template>\n"
        f"{template.strip()}\n"
        "</parameter>\n"
        "</function>\n"
        "</tool_call>"
    )


def build_row(record: dict[str, Any], *, row_id: str, source: str, output_format: str) -> dict[str, Any] | None:
    output = record.get("output")
    if not isinstance(output, str) or not output.strip():
        return None

    user_request = record.get("user_request")
    if not isinstance(user_request, str) or not user_request.strip():
        task_type = record.get("task_type")
        if task_type == "autocomplete_next_operations":
            user_request = "Continue the CAD history by adding the next valid CAD operations."
        else:
            user_request = "Apply the selected CAD template edit using the provided CAD history and anchor."

    selection = record.get("selection") if isinstance(record.get("selection"), str) else ""
    anchor = record.get("anchor") if isinstance(record.get("anchor"), str) else ""
    history = record.get("history") if isinstance(record.get("history"), str) else ""
    anchor_point = parse_anchor_point(anchor)
    feature_id = parse_insert_before_id(str(record.get("user_request") or "")) or parse_selected_feature(selection) or "end"

    prompt = build_prompt(
        user_request,
        selection=selection,
        feature_id=feature_id,
        anchor_point=anchor_point,
        history=history,
    )
    spec = {
        "slug": row_id,
        "source": source,
        "source_task_type": record.get("task_type"),
        "reference_template": output.strip(),
        "scale_critical": True,
    }
    answer = wrap_template(output)
    grade = grade_answer(answer, spec)
    if grade.reward < 0.99:
        return None

    if output_format == "sft":
        return {
            "messages": [
                {"role": "user", "content": prompt},
                {"role": "assistant", "content": answer},
            ]
        }

    if output_format == "eval-protocol":
        return {
            "messages": [{"role": "user", "content": prompt}],
            "input_metadata": {
                "row_id": row_id,
                "completion_params": {},
                "dataset_info": {
                    "slug": row_id,
                    "source": source,
                    "spec": spec,
                },
            },
            "ground_truth": spec,
        }

    raise ValueError(f"unsupported output format: {output_format}")


def parse_anchor_point(anchor: str) -> str:
    match = re.search(r"anchor_point=(.+)", anchor)
    return match.group(1).strip() if match else ""


def parse_selected_feature(selection: str) -> str | None:
    for line in selection.splitlines():
        if line.startswith("selected_feature="):
            value = line.split("=", 1)[1].strip()
            return value or None
    return None


def parse_insert_before_id(text: str) -> str | None:
    match = re.search(r"\bbefore\s+([A-Za-z]+_\d+)\b", text)
    return match.group(1) if match else None


def iter_jsonl(path: Path):
    with path.open() as file:
        for line_number, line in enumerate(file, start=1):
            if line.strip():
                yield line_number, json.loads(line)


def build_dataset(args: argparse.Namespace) -> int:
    testing_root = Path(args.testing_root)
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)

    written = 0
    skipped = 0
    sources = args.source or list(DEFAULT_SOURCES)
    with output.open("w") as out:
        for source in sources:
            path = testing_root / source
            if not path.exists():
                raise FileNotFoundError(path)

            source_written = 0
            for line_number, record in iter_jsonl(path):
                if args.max_history_chars and len(str(record.get("history", ""))) > args.max_history_chars:
                    skipped += 1
                    continue
                row = build_row(
                    record,
                    row_id=f"{path.stem}-{line_number}",
                    source=str(path),
                    output_format=args.format,
                )
                if row is None:
                    skipped += 1
                    continue
                out.write(json.dumps(row, separators=(",", ":")) + "\n")
                written += 1
                source_written += 1
                if args.max_rows_per_source and source_written >= args.max_rows_per_source:
                    break

    print(f"wrote {written} rows to {output}; skipped {skipped}")
    return written


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build a Fireworks/Eval Protocol dataset from DeepCAD-derived JSONLs.")
    parser.add_argument("--testing-root", default=str(DEFAULT_TESTING_ROOT))
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT))
    parser.add_argument("--source", action="append", help="Source JSONL under testing-root; may be passed multiple times.")
    parser.add_argument("--format", choices=("eval-protocol", "sft"), default="eval-protocol")
    parser.add_argument("--max-rows-per-source", type=int, default=500)
    parser.add_argument("--max-history-chars", type=int, default=24000)
    return parser.parse_args()


if __name__ == "__main__":
    raise SystemExit(0 if build_dataset(parse_args()) else 1)
