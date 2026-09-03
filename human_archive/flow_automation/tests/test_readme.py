from pathlib import Path

README = Path(__file__).parents[1] / 'README.md'

def test_runbook_contains_required_recovery_paths() -> None:
    text = README.read_text(encoding='utf-8')
    for phrase in ['Load unpacked', 'Generate Missing', 'PROJECT_MISMATCH', 'AMBIGUOUS_RESULT', 'FLOW_UI_CHANGED', 'Resume', 'uninstall']:
        assert phrase in text
