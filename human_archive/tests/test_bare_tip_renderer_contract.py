from __future__ import annotations

import importlib.util
from pathlib import Path


PIPELINE = Path(__file__).parents[1] / "scripts" / "run_neanderthal_full_pipeline.py"


def _load_pipeline():
    spec = importlib.util.spec_from_file_location("nollam_pipeline_for_bare_tip_test", PIPELINE)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_bare_tip_command_uses_canonical_external_renderer(tmp_path) -> None:
    module = _load_pipeline()
    command = module.build_bare_tip_command(Path("source.jpg"), tmp_path, 11.0, fps=25)
    assert command[0].endswith("python.exe") or command[0].endswith("python")
    assert command[1].endswith("srt-whiteboard-animation\\scripts\\stream_render.py")
    assert "--bare-tip" in command
    assert command[command.index("--total-ms") + 1] == "11000"
    assert command[command.index("--fps") + 1] == "25"


def test_pipeline_rejects_placeholder_opening_fallback() -> None:
    source = PIPELINE.read_text(encoding="utf-8")
    assert "refusing to synthesize a placeholder opening asset" in source
    assert "refusing to reuse a placeholder asset" in source


def test_pipeline_uses_canonical_semantic_subtitle_engine() -> None:
    module = _load_pipeline()
    content = module.generate_ass_subtitles([
        {
            "display_text": "빙하기의 혹독한 기후 변화와 사냥 경쟁은 두 인류 집단의 운명을 서서히 갈라놓았습니다.",
            "speech_start": 0.0,
            "speech_end": 8.0,
        }
    ])
    dialogue = next(line for line in content.splitlines() if line.startswith("Dialogue:"))
    subtitle_text = dialogue.split(",", 9)[9]
    assert "DocuNarrator_v4" in dialogue
    assert subtitle_text.count(r"\N") <= 1
    assert all(len(line) <= 36 for line in subtitle_text.split(r"\N"))
