from pathlib import Path

import pytest

from human_archive.scripts.lib.artifact_lineage import (
    canonical_payload_sha256,
    envelope_core_sha256,
    validate_parent_matrix,
)


def test_canonical_hash_is_key_order_independent():
    assert canonical_payload_sha256({"b": 2, "a": 1}) == canonical_payload_sha256({"a": 1, "b": 2})


def test_envelope_core_excludes_created_at_and_self_digest():
    base = {"artifact_id": "a", "payload_sha256": "A", "created_at": "one"}
    changed = {**base, "created_at": "two", "envelope_core_sha256": "old"}
    assert envelope_core_sha256(base) == envelope_core_sha256(changed)


def test_parent_matrix_requires_scope_and_two_digests():
    with pytest.raises(ValueError):
        validate_parent_matrix("verified_script_v3", [{"artifact_id": "x"}], {"scope_kind": "quick_3m"})


def test_missing_parent_digest_is_rejected():
    with pytest.raises(ValueError):
        validate_parent_matrix("verified_script_v3", [{"artifact_id": "x", "payload_sha256": "A"}], {"scope_kind": "quick_3m"})
