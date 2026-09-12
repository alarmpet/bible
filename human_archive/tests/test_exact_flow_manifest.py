import json
import sys
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parent.parent / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from build_exact_flow_request_manifest import build_manifest


def test_exact_flow_manifest_contains_one_request_per_ab_plate(tmp_path: Path) -> None:
    plan = tmp_path / "plates.json"
    output = tmp_path / "generation" / "image_request_manifest.json"
    plan.write_text(
        json.dumps(
            {
                "plates": [
                    {"plate_id": "SHOT_001_A", "parent_shot_id": "SHOT_001", "flow_prompt_en": "scene A"},
                    {"plate_id": "SHOT_001_B", "parent_shot_id": "SHOT_001", "flow_prompt_en": "scene B"},
                ]
            }
        ),
        encoding="utf-8",
    )

    result = build_manifest(plan, output, expected_count=2)
    data = json.loads(output.read_text(encoding="utf-8"))

    assert result == output
    assert [row["scene_id"] for row in data["requests"]] == ["SHOT_001_A", "SHOT_001_B"]
    assert all(row["submission_prompt"].startswith("2D graphic novel illustration") for row in data["requests"])
    assert all(len(row["submission_prompt"]) <= 441 for row in data["requests"])
    assert data["project_id"] == "8550306b-a63c-450f-beda-5ed1d72a760e"
    assert all(len(row["request_sha256"]) == 64 for row in data["requests"])
