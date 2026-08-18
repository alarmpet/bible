# -*- coding: utf-8 -*-
"""Unit tests for the CosyVoice3 adapter. No model download required."""
from __future__ import annotations

from pathlib import Path
import sys

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from cosyvoice3_engine import default_instruct_for, resolve_voice_spec  # noqa: E402
from cosyvoice3_worker import _split_clauses  # noqa: E402


def test_default_instruct_male_is_calm_not_angry():
    text = default_instruct_for("M4", 0.95)
    assert "Korean" in text
    assert "never angry" in text
    assert "0.95" in text
    assert text.endswith("<|endofprompt|>")


def test_default_instruct_female_is_healing_narrator():
    text = default_instruct_for("F5", 0.95)
    assert "female narrator" in text
    assert "healing" in text


def test_voice_map_resolves_m4_and_f5():
    m4 = resolve_voice_spec("M4", 0.95)
    f5 = resolve_voice_spec("F5", 0.95)
    assert m4["mode"] == "instruct2"
    assert f5["mode"] == "instruct2"
    assert "scripture_M4_ref.wav" in (m4.get("ref_wav") or "")
    assert "narrator_F5_ref.wav" in (f5.get("ref_wav") or "")
    assert "pastor" in (m4.get("instruct") or "").lower() or "male" in (m4.get("instruct") or "").lower()


def test_clause_split_does_not_cut_yhwh():
    text = "여호와는 나의 목자시니 내게 부족함이 없으리로다."
    parts = _split_clauses(text, 90)
    assert parts
    joined = "".join(parts)
    assert "여호와" in joined
    assert all("여" != p and not p.startswith("호와") for p in parts)


def test_tts_wrapper_defaults_engine():
    src = (SCRIPTS / "tts_multi_voice_cosyvoice.py").read_text(encoding="utf-8")
    assert "--engine" in src
    assert "cosyvoice3" in src
    main = (SCRIPTS / "tts_multi_voice.py").read_text(encoding="utf-8")
    assert '--engine' in main
    assert 'default="supertonic3"' in main
