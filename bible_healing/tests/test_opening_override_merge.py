import sys
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))
from build_episode import merge_bank_override  # noqa: E402


def test_opening_override_can_shorten_redundant_first_unit_intro():
    merged = merge_bank_override(
        {"opening": [], "units": {"u01": {"before": "긴 기존 문장", "after": "후속"}}},
        {"units": {"u01": {"before": ""}}},
    )
    assert merged["units"]["u01"]["before"] == ""
    assert merged["units"]["u01"]["after"] == "후속"
