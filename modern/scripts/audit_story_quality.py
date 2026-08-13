#!/usr/bin/env python3
"""Audit a generated story and emit a machine-readable QA report."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import Any

import yaml


ROOT = Path(__file__).parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from modern.story_quality import (  # noqa: E402
    check_filler_repetition,
    load_yaml,
    validate_project_contract,
)


def load_mapping_document(path: Path) -> dict[str, Any]:
    """Load YAML or YAML front matter from a UTF-8 document."""

    if path.suffix.lower() in {".yaml", ".yml"}:
        return load_yaml(path)
    text = path.read_text(encoding="utf-8")
    if text.startswith("---"):
        parts = text.split("---", 2)
        value = yaml.safe_load(parts[1])
        if isinstance(value, dict):
            return value
    raise ValueError(f"YAML_OR_FRONT_MATTER_REQUIRED: {path}")


def merge_reports(*reports: dict[str, object]) -> dict[str, object]:
    blocks: list[str] = []
    warns: list[str] = []
    measures: dict[str, object] = {}
    for index, report in enumerate(reports, start=1):
        blocks.extend(str(item) for item in report.get("blocks", []))
        warns.extend(str(item) for item in report.get("warns", []))
        measures[f"check_{index}"] = report.get("measures", {})
    return {"ok": not blocks, "blocks": blocks, "warns": warns, "measures": measures}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--text", required=True, type=Path, help="UTF-8 final story text")
    parser.add_argument("--contract", type=Path, help="project_contract YAML")
    parser.add_argument("--source-packet", type=Path, help="source packet YAML/Markdown")
    parser.add_argument("--output", type=Path, help="optional JSON report path")
    return parser.parse_args()


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    args = parse_args()
    text = args.text.read_text(encoding="utf-8")
    contract = load_mapping_document(args.contract) if args.contract else None
    source_packet = (
        load_mapping_document(args.source_packet) if args.source_packet else None
    )
    allowlist = contract.get("filler_allowlist", []) if contract else []

    reports = [check_filler_repetition(text, allowlist=allowlist)]
    if contract is not None:
        reports.append(validate_project_contract(contract, source_packet))
    report = merge_reports(*reports)
    rendered = json.dumps(report, ensure_ascii=False, indent=2) + "\n"

    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered, encoding="utf-8")
    else:
        sys.stdout.write(rendered)
    return 0 if report["ok"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
