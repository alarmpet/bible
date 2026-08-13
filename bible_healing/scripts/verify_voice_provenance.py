# -*- coding: utf-8 -*-
"""Lock enforcement, verse-level TTS prep, and tts_provenance.json checks."""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

from sanitize_script import assert_no_emotion_triggers, sanitize_script
from scripture_tts_prep import split_into_speech_units

_BH_ROOT = Path(__file__).resolve().parents[1]
_LOCK_PATH = _BH_ROOT / "config" / "media_rules_lock.json"

PROVENANCE_FIELDS = (
    "speaker",
    "voice",
    "speed",
    "total_step",
    "max_chunk",
    "text",
    "text_sha256",
    "wav_sha256",
    "filter_applied",
)

_DEFAULT_STEP_WHEN_PENDING = 10


def load_media_lock(path: Path | None = None) -> dict:
    return json.loads((path or _LOCK_PATH).read_text(encoding="utf-8"))


def resolve_total_step(speaker: str, lock: dict | None = None) -> int:
    lock = lock or load_media_lock()
    spec = (lock.get("voice") or {}).get(speaker) or {}
    raw = spec.get("total_step")
    forbidden = set((lock.get("voice") or {}).get("scripture", {}).get("forbidden_total_step") or [24])
    if raw in (None, "pending_ab"):
        step = _DEFAULT_STEP_WHEN_PENDING
    else:
        step = int(raw)
    if step in forbidden:
        raise SystemExit(f"voice lock: forbidden total_step={step} for {speaker}")
    return step


def enforce_skip_existing(skip_existing: bool, lock: dict | None = None) -> None:
    lock = lock or load_media_lock()
    if skip_existing and (lock.get("tts") or {}).get("skip_existing_forbidden"):
        raise SystemExit(
            "skip-existing is forbidden by media_rules_lock.tts.skip_existing_forbidden"
        )


def enforce_voice_map(speakers: dict, lock: dict | None = None) -> None:
    lock = lock or load_media_lock()
    allowed = list(lock.get("speakers") or ["narrator", "scripture"])
    voice_lock = lock.get("voice") or {}
    for sid in allowed:
        if sid not in speakers:
            raise SystemExit(f"voice lock: missing speaker {sid}")
        got_voice = speakers[sid].get("voice")
        want_voice = voice_lock[sid]["voice"]
        if got_voice != want_voice:
            raise SystemExit(
                f"voice lock: {sid} voice {got_voice!r} != locked {want_voice!r}"
            )
        got_speed = float(speakers[sid].get("speed"))
        want_speed = float(voice_lock[sid]["speed"])
        if abs(got_speed - want_speed) > 1e-6:
            raise SystemExit(
                f"voice lock: {sid} speed {got_speed} != locked {want_speed}"
            )
    extra = set(speakers) - set(allowed)
    if extra:
        raise SystemExit(f"voice lock: extra speakers {sorted(extra)}")


def run_job_preflight(job: Path, skip_existing: bool, lock: dict | None = None) -> dict:
    """Reject --skip-existing and non-lock voices before any SuperTonic import."""
    lock = lock or load_media_lock()
    enforce_skip_existing(skip_existing, lock)
    vm_path = Path(job) / "voice_map.json"
    vm = json.loads(vm_path.read_text(encoding="utf-8"))
    enforce_voice_map(vm.get("speakers") or {}, lock)
    return lock


def prepare_speech_units(text: str, speaker: str, lock: dict | None = None) -> list[str]:
    """Sanitize then (for scripture) split so every synthesize unit is <= max_chunk."""
    lock = lock or load_media_lock()
    sanitized = sanitize_script(text).tts
    if not sanitized.strip():
        raise ValueError("empty sanitized tts text")
    assert_no_emotion_triggers(sanitized)
    if speaker == "scripture":
        max_len = int((lock.get("voice") or {}).get("scripture", {}).get("max_chunk_length") or 90)
        units = split_into_speech_units(sanitized, max_len=max_len)
        if not units:
            raise ValueError("empty sanitized tts text")
        over = [u for u in units if len(u) > max_len]
        if over:
            raise ValueError(f"speech unit exceeds max_len={max_len}: {over[0][:40]!r}")
        for unit in units:
            assert_no_emotion_triggers(unit)
        return units
    return [sanitized]


def sha256_text(text: str) -> str:
    return hashlib.sha256((text or "").encode("utf-8")).hexdigest()


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with Path(path).open("rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def build_piece_provenance(
    *,
    speaker: str,
    voice: str,
    speed: float,
    total_step: int,
    max_chunk: int,
    text: str,
    wav_path: Path,
    filter_applied: bool,
    **extra,
) -> dict:
    rec = {
        "speaker": speaker,
        "voice": voice,
        "speed": float(speed),
        "total_step": int(total_step),
        "max_chunk": int(max_chunk),
        "text": text,
        "text_sha256": sha256_text(text),
        "wav_sha256": sha256_file(wav_path) if Path(wav_path).exists() else "",
        "filter_applied": bool(filter_applied),
    }
    rec.update(extra)
    return rec


def write_tts_provenance(job: Path, pieces: list[dict], extra: dict | None = None) -> Path:
    payload: dict = {"ok": True, "engine": "supertonic3", "pieces": pieces}
    if extra:
        payload.update(extra)
    out = Path(job) / "reports" / "tts_provenance.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return out


def verify_tts_provenance(path: Path) -> dict:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    pieces = data.get("pieces") or []
    errors: list[str] = []
    if not pieces:
        errors.append("no pieces")
    for i, piece in enumerate(pieces):
        missing = [k for k in PROVENANCE_FIELDS if k not in piece]
        if missing:
            errors.append(f"piece[{i}] missing {missing}")
            continue
        if piece.get("speaker") == "scripture":
            if piece.get("voice") != "M4":
                errors.append(f"piece[{i}] scripture voice {piece.get('voice')!r} != M4")
            if not piece.get("filter_applied"):
                errors.append(f"piece[{i}] scripture filter_applied is not true")
            text = piece.get("text") or ""
            if any(ch in text for ch in "!?！？❗"):
                errors.append(f"piece[{i}] emotion punctuation remains in text")
            if int(piece.get("max_chunk") or 0) > 90:
                errors.append(f"piece[{i}] max_chunk > 90")
            if int(piece.get("total_step") or 0) == 24:
                errors.append(f"piece[{i}] forbidden total_step 24")
    if errors:
        raise SystemExit("tts provenance failed: " + "; ".join(errors))
    return {"ok": True, "pieces": len(pieces)}


def main() -> None:
    ap = argparse.ArgumentParser(description="Verify reports/tts_provenance.json")
    ap.add_argument("--job", required=True)
    args = ap.parse_args()
    result = verify_tts_provenance(Path(args.job) / "reports" / "tts_provenance.json")
    print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    main()
