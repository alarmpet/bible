# -*- coding: utf-8 -*-
import importlib.util
import sys
from pathlib import Path

BUILD = Path(__file__).resolve().parents[1] / "runs" / "nollam_file" / "2026-09-01" / "nepal-tunnel-rescue" / "20260901-kr-nepal-tunnel-v3" / "build_v3.py"
spec = importlib.util.spec_from_file_location("nepal_build_v3", BUILD)
build_v3 = importlib.util.module_from_spec(spec)
assert spec.loader is not None
sys.modules[spec.name] = build_v3
spec.loader.exec_module(build_v3)

LONG_TEXT = "AP가 인용한 기후·지질 전문가들은 빙하 아래 기반암이 무너지며 얼음과 바위, 녹은 물이 한꺼번에 계곡으로 쏟아진 연쇄 붕괴를 이번 홍수의 발단으로 설명했다."

def _norm(text: str) -> str:
    return " ".join(text.split())

def _sentence():
    return [{"sentence_id": "S001", "tts_text": LONG_TEXT, "start_sec": 0.0, "end_sec": 12.0}]

def test_write_ass_preserves_long_caption_without_double_escaping(tmp_path):
    out = tmp_path / "subtitles.ass"
    build_v3.write_ass(_sentence(), out)
    text = out.read_text(encoding="utf-8-sig")
    dialogues = [line for line in text.splitlines() if line.startswith("Dialogue:")]
    assert len(dialogues) > 1
    assert r"\\N" not in "\n".join(dialogues)
    payload = " ".join(line.rsplit(",,", 1)[1].replace(r"\N", " ") for line in dialogues)
    assert _norm(payload) == _norm(LONG_TEXT)

def test_write_srt_preserves_full_caption_with_two_line_events(tmp_path):
    out = tmp_path / "subtitles.srt"
    build_v3.write_srt(_sentence(), out)
    text = out.read_text(encoding="utf-8")
    assert text.count("-->") > 1
    caption_lines = [line for line in text.splitlines() if line and not line.isdigit() and "-->" not in line]
    assert all(len(line) <= 28 for line in caption_lines)
    assert _norm(" ".join(caption_lines)) == _norm(LONG_TEXT)
