from __future__ import annotations

from pathlib import Path
import yaml


ROOT = Path(__file__).resolve().parents[1]


def resolve_nollam_tts_lock() -> dict[str, object]:
    policy = yaml.safe_load((ROOT / "config" / "nollam_file_narration_policy.yaml").read_text(encoding="utf-8"))
    expected = {"voice_lock_id": "M2_WARM", "voice": "M2", "speed": 0.95, "total_step": 10}
    actual = {key: policy.get(key) for key in expected}
    if actual != expected:
        raise ValueError(f"M2_WARM lock mismatch: expected {expected}, got {actual}")
    return actual


def build_nollam_audio(*args, **kwargs):
    """Invoke the existing builder only after the Nollam lock is verified."""
    from human_archive.scripts.build_sentence_audio_master import build_sentence_audio_master

    lock = resolve_nollam_tts_lock()
    kwargs.setdefault("audio_mode", "supertonic3")
    kwargs.update({"voice": lock["voice"], "speed": lock["speed"], "total_step": lock["total_step"], "voice_lock_id": lock["voice_lock_id"]})
    return build_sentence_audio_master(*args, **kwargs)
