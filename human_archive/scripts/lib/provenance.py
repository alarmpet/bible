# -*- coding: utf-8 -*-
"""Canonical JSON serialization and cryptographic hash chaining utilities."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any


def canonical_json_bytes(obj: Any) -> bytes:
    """Serialize Python object to RFC 8785 canonical JSON bytes (NFC normalized, sorted keys, no whitespace)."""
    # Deterministic JSON serialization: sorted keys, separators=(',', ':'), UTF-8 encoding
    return json.dumps(obj, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode("utf-8")


def compute_object_sha256(obj: Any) -> str:
    """Compute SHA-256 hash of canonical JSON bytes of an object."""
    raw = canonical_json_bytes(obj)
    return hashlib.sha256(raw).hexdigest().upper()


def compute_file_sha256(path: Path) -> str:
    """Compute SHA-256 hash of a file on disk."""
    hasher = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(65536):
            hasher.update(chunk)
    return hasher.hexdigest().upper()
