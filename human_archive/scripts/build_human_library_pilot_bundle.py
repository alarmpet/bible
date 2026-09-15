# -*- coding: utf-8 -*-
"""
build_human_library_pilot_bundle.py
Extracts and validates Pilot-5 (SHOT_001 ~ SHOT_005, 20.6s) from normalized_replica_bundle.json.
Conforms strictly to human_library_replica_contract_v1.schema.json.
"""

from __future__ import annotations

import json
from pathlib import Path
from jsonschema import validate, ValidationError

SCRIPTS_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPTS_DIR.parent
RUN_DIR = REPO_ROOT / "runs" / "human_library_replica" / "rank1_race_adaptation"
METADATA_DIR = RUN_DIR / "metadata"
SCHEMA_FILE = REPO_ROOT / "schemas" / "human_library_replica_contract_v1.schema.json"
BUNDLE_FILE = METADATA_DIR / "normalized_replica_bundle.json"
PILOT_BUNDLE_FILE = METADATA_DIR / "pilot_5_bundle.json"


def build_pilot_5_bundle() -> dict:
    if not BUNDLE_FILE.exists():
        raise FileNotFoundError(f"Canonical bundle missing: {BUNDLE_FILE}")
    if not SCHEMA_FILE.exists():
        raise FileNotFoundError(f"Schema file missing: {SCHEMA_FILE}")

    with open(BUNDLE_FILE, "r", encoding="utf-8") as f:
        master_bundle = json.load(f)

    with open(SCHEMA_FILE, "r", encoding="utf-8") as f:
        schema = json.load(f)

    pilot_shots = [s for s in master_bundle["shots"] if s["order"] <= 5]
    if len(pilot_shots) != 5:
        raise ValueError(f"Expected exactly 5 pilot shots, got {len(pilot_shots)}")

    total_pilot_duration = round(sum(s["duration_sec"] for s in pilot_shots), 3)
    if total_pilot_duration != 20.6:
        raise ValueError(f"Expected total pilot duration 20.6s, got {total_pilot_duration}s")

    all_sentences = []
    for s in pilot_shots:
        all_sentences.extend(s["sentence_spans"])

    pilot_bundle = {
        "schema_version": 1,
        "episode_id": f"{master_bundle['episode_id']}_pilot5",
        "title": f"{master_bundle['title']} (Pilot-5 20.6s)",
        "target_duration_sec": total_pilot_duration,
        "total_shots": 5,
        "total_sentences": len(all_sentences),
        "pacing_summary": {
            "opening_cuts": 3,
            "tier1_cuts": 2,
            "tier2_cuts": 0,
            "tier3_cuts": 0,
        },
        "shots": pilot_shots,
    }

    # Validate against JSON schema
    validate(instance=pilot_bundle, schema=schema)

    with open(PILOT_BUNDLE_FILE, "w", encoding="utf-8") as f:
        json.dump(pilot_bundle, f, indent=2, ensure_ascii=False)

    print(f"[OK] Generated and validated Pilot-5 bundle: {PILOT_BUNDLE_FILE}")
    print(f"     Total shots: {pilot_bundle['total_shots']}, Duration: {pilot_bundle['target_duration_sec']}s")
    print(f"     Sentences: {all_sentences}")
    return pilot_bundle


if __name__ == "__main__":
    build_pilot_5_bundle()
