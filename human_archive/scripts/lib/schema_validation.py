# -*- coding: utf-8 -*-
"""JSON Schema validation utility for all CLI boundaries."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any
import jsonschema


def validate_json(instance: dict[str, Any], schema: dict[str, Any]) -> None:
    """Validate JSON instance against schema, raising ValueError on failure."""
    validator = jsonschema.Draft202012Validator(schema)
    errors = sorted(validator.iter_errors(instance), key=lambda e: e.path)
    if errors:
        msg = "; ".join(f"[{'/'.join(map(str, e.path))}] {e.message}" for e in errors)
        raise ValueError(f"Schema validation failed: {msg}")


def load_schema(schema_path: Path) -> dict[str, Any]:
    return json.loads(schema_path.read_text(encoding="utf-8"))
