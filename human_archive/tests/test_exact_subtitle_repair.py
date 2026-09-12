from pathlib import Path

from lib.exact_subtitle_repair import convert_ass_to_one_line
from lib.exact_release_verifier import audit_ass_strict


def test_convert_ass_to_one_line_splits_multiline_events_without_overlap(tmp_path: Path) -> None:
    source = tmp_path / "source.ass"
    target = tmp_path / "target.ass"
    source.write_text(
        """[Script Info]\nPlayResX: 1920\nPlayResY: 1080\n\n[Events]\nFormat: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text\nDialogue: 0,0:00:01.00,0:00:03.00,DocuNarrator_Exact,,0,0,0,,첫 줄\\N둘째 줄\n""",
        encoding="utf-8",
    )

    metrics = convert_ass_to_one_line(source, target)

    assert metrics["multiline_input"] == 1
    assert metrics["dialogue_output"] == 2
    check = audit_ass_strict(target, target_duration_sec=3.0)
    assert check["status"] == "PASS", check["errors"]
    assert check["multiline_events"] == 0

