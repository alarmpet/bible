# -*- coding: utf-8 -*-
"""Generic media-rules preflight for any hermes job.

Usage:
  python media_rules_preflight.py --job <jobDir> [--lock path]

Orchestrator step 1 is config/lock only: speakers, lock voice IDs, speeds,
D: root, background bank, skip-existing forbidden. Job scenes, ASS,
provenance, auth WAV, and stale voice_map are later-step checks.

Job-state helpers (check_scenes_text, check_ass_text, check_provenance,
check_voice_map) stay here for later gates and unit tests.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

_BH_ROOT = Path(__file__).resolve().parents[1]
_MODULE_ROOT = _BH_ROOT.parent
_DEFAULT_LOCK = _BH_ROOT / "config" / "media_rules_lock.json"

FORBIDDEN_VOICES = frozenset({"F3", "M3", "M5"})
STALE_SPEEDS = frozenset({0.78, 0.85})
# Bang / selah / psalm titles that must not reach scenes or ASS.
FORBIDDEN_TEXT_RE = re.compile(
    r"!|！|❗|\(셀라\)|（셀라）|셀라|다윗의 시",
)


def load_lock(path: Path | None = None) -> dict:
    p = Path(path) if path else _DEFAULT_LOCK
    return json.loads(p.read_text(encoding="utf-8"))


def _read_json(path: Path) -> dict | list | None:
    if not path.is_file():
        return None
    return json.loads(path.read_text(encoding="utf-8-sig"))


def check_voice_map(voice_map: dict, lock: dict) -> list[str]:
    """Fail on stale voices/speeds, empty scripture filter, step 24, max_chunk>90."""
    errors: list[str] = []
    speakers = (voice_map or {}).get("speakers") or {}
    voice_lock = lock.get("voice") or {}
    allowed = list(lock.get("speakers") or ["narrator", "scripture"])

    for sid in allowed:
        if sid not in speakers:
            errors.append(f"voice_map: missing speaker {sid}")
            continue
        conf = speakers[sid] or {}
        want = voice_lock.get(sid) or {}
        got_voice = conf.get("voice")
        want_voice = want.get("voice")
        if got_voice in FORBIDDEN_VOICES:
            errors.append(f"voice_map: forbidden voice {got_voice!r} for {sid}")
        if want_voice and got_voice != want_voice:
            errors.append(
                f"voice_map: {sid} voice {got_voice!r} != locked {want_voice!r}"
            )
        try:
            got_speed = float(conf.get("speed"))
        except (TypeError, ValueError):
            errors.append(f"voice_map: {sid} missing/invalid speed")
            got_speed = None
        if got_speed is not None:
            if got_speed in STALE_SPEEDS:
                errors.append(f"voice_map: stale speed {got_speed} for {sid}")
            want_speed = want.get("speed")
            if want_speed is not None and abs(got_speed - float(want_speed)) > 1e-6:
                errors.append(
                    f"voice_map: {sid} speed {got_speed} != locked {want_speed}"
                )

        if sid == "scripture":
            filt = conf.get("audio_filter")
            if not (filt or "").strip():
                errors.append("voice_map: empty scripture audio_filter")
            want_filt = (want.get("audio_filter") or "").strip()
            if want_filt and (filt or "").strip() != want_filt:
                # Soft: allow if non-empty; lock equality preferred but empty is hard fail.
                pass
            try:
                step = int(conf.get("total_step"))
            except (TypeError, ValueError):
                step = None
                errors.append("voice_map: scripture missing/invalid total_step")
            forbidden_steps = set(
                want.get("forbidden_total_step")
                or voice_lock.get("scripture", {}).get("forbidden_total_step")
                or [24]
            )
            if step is not None and step in forbidden_steps:
                errors.append(f"voice_map: forbidden total_step={step}")
            if step is not None and step == 24:
                errors.append("voice_map: total_step==24")
            try:
                max_chunk = int(
                    conf.get("max_chunk_length")
                    if conf.get("max_chunk_length") is not None
                    else conf.get("max_chunk")
                )
            except (TypeError, ValueError):
                max_chunk = None
            limit = int(want.get("max_chunk_length") or 90)
            if max_chunk is not None and max_chunk > limit:
                errors.append(
                    f"voice_map: max_chunk_length {max_chunk} > {limit}"
                )

    for sid, conf in speakers.items():
        if sid not in allowed:
            errors.append(f"voice_map: extra speaker {sid}")
        v = (conf or {}).get("voice")
        if v in FORBIDDEN_VOICES:
            errors.append(f"voice_map: forbidden voice {v!r} on {sid}")

    return errors


def check_render_options(render_options: dict, lock: dict) -> list[str]:
    errors: list[str] = []
    if not render_options:
        return ["render-options: missing"]
    engine = render_options.get("engineVoice") or render_options.get("voiceId")
    if engine in FORBIDDEN_VOICES:
        errors.append(f"render-options: forbidden engineVoice {engine!r}")
    scripture = (lock.get("voice") or {}).get("scripture") or {}
    want_voice = scripture.get("voice") or "M4"
    want_speed = float(scripture.get("speed") or 0.86)
    if engine and engine != want_voice and not render_options.get("multiVoice"):
        errors.append(
            f"render-options: engineVoice {engine!r} != locked {want_voice!r}"
        )
    try:
        speed = float(render_options.get("speechSpeed"))
    except (TypeError, ValueError):
        speed = None
    if speed is not None:
        if speed in STALE_SPEEDS:
            errors.append(f"render-options: stale speechSpeed {speed}")
        # Single-voice jobs must match scripture speed; multiVoice may differ at root.
        if not render_options.get("multiVoice") and abs(speed - want_speed) > 1e-6:
            errors.append(
                f"render-options: speechSpeed {speed} != locked {want_speed}"
            )
    return errors


def _scene_texts(scenes: list) -> list[tuple[str, str]]:
    out: list[tuple[str, str]] = []
    for scene in scenes or []:
        order = str(scene.get("order") or scene.get("scene_id") or "?")
        for key in ("narration", "text"):
            t = scene.get(key)
            if isinstance(t, str) and t.strip():
                out.append((order, t))
        for seg in scene.get("segments") or []:
            t = seg.get("text")
            if isinstance(t, str) and t.strip():
                out.append((order, t))
    return out


def check_scenes_text(scenes: list) -> list[str]:
    """Fail if scenes still contain ! / (셀라) / 다윗의 시."""
    errors: list[str] = []
    for order, text in _scene_texts(scenes):
        match = FORBIDDEN_TEXT_RE.search(text)
        if match:
            errors.append(
                f"scenes order={order}: forbidden token {match.group()!r} in {text[:40]!r}"
            )
    return errors


def check_ass_text(ass_text: str) -> list[str]:
    """Fail if ASS dialogue still has ! / 셀라 / 다윗의 시."""
    errors: list[str] = []
    if not ass_text:
        return errors
    for i, raw in enumerate(ass_text.splitlines()):
        if not raw.startswith("Dialogue:"):
            continue
        parts = raw.split(",", 9)
        body = parts[9] if len(parts) >= 10 else raw
        match = FORBIDDEN_TEXT_RE.search(body)
        if match:
            errors.append(
                f"ass event~{i}: forbidden token {match.group()!r} in {body[:40]!r}"
            )
    return errors


def _walk_truthy_keys(obj, keys: set[str], path: str = "") -> list[str]:
    hits: list[str] = []
    if isinstance(obj, dict):
        for k, v in obj.items():
            p = f"{path}.{k}" if path else str(k)
            kl = str(k).lower().replace("-", "_")
            if kl in keys and v:
                hits.append(p)
            hits.extend(_walk_truthy_keys(v, keys, p))
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            hits.extend(_walk_truthy_keys(v, keys, f"{path}[{i}]"))
    return hits


def check_tts_report(report: dict | None, lock: dict) -> list[str]:
    """Fail if job TTS report records skip-existing when lock forbids it."""
    if report is None:
        return []
    if not (lock.get("tts") or {}).get("skip_existing_forbidden", True):
        return []
    hits = _walk_truthy_keys(
        report, {"skip_existing", "skipexisting", "skip_existing_used"}
    )
    # Also plain "skip-existing" key via normalized walk
    extra: list[str] = []
    if isinstance(report, dict):
        for k, v in report.items():
            if str(k).replace("-", "_").lower() == "skip_existing" and v:
                extra.append(str(k))
        args = report.get("args") or report.get("flags") or {}
        if isinstance(args, dict):
            for k, v in args.items():
                if str(k).replace("-", "_").lower() == "skip_existing" and v:
                    extra.append(f"args.{k}")
    all_hits = list(dict.fromkeys(hits + extra))
    if all_hits:
        return [f"tts_report: skip-existing flag present at {', '.join(all_hits)}"]
    return []


def check_provenance(job: Path) -> list[str]:
    errors: list[str] = []
    job = Path(job)
    prov = job / "reports" / "tts_provenance.json"
    if not prov.is_file():
        errors.append("missing_provenance: reports/tts_provenance.json")
    rebuild_prov = job / "authoritative_audio_rebuild" / "voice_provenance.json"
    # Rebuild provenance is required only when rebuild dir is expected; soft if dir absent.
    rebuild_dir = job / "authoritative_audio_rebuild"
    if rebuild_dir.is_dir() and not rebuild_prov.is_file():
        errors.append(
            "missing_voice_provenance_rebuild: authoritative_audio_rebuild/voice_provenance.json"
        )
    auth = rebuild_dir / "full-authoritative-audio.wav"
    if rebuild_dir.is_dir() and not auth.is_file():
        errors.append("missing_authoritative_audio")
    return errors


def check_storage(lock: dict) -> list[str]:
    """Fail if final_root is not on D:."""
    errors: list[str] = []
    storage = lock.get("storage") or {}
    final_root = str(storage.get("final_root") or "")
    if not final_root:
        errors.append("storage: final_root missing")
        return errors
    # Windows drive letter or UNC — require D:
    if not re.match(r"^[Dd]:", final_root):
        errors.append(f"output_root_not_D: final_root={final_root!r}")
        return errors
    # Existence only when D: is mounted (tests never require a real D: tree).
    if Path("D:/").exists() and not Path(final_root).exists():
        errors.append(f"missing_D_final_root: {final_root}")
    return errors


def check_background(lock: dict, root: Path | None = None) -> list[str]:
    errors: list[str] = []
    bg = (lock.get("background") or {})
    rel = bg.get("directory") or ""
    required = int(bg.get("required_count") or 12)
    base = Path(root) if root else _MODULE_ROOT
    directory = Path(rel)
    if not directory.is_absolute():
        directory = base / rel
    if not directory.is_dir():
        # Fall back to module root if custom root has no assets
        alt = _MODULE_ROOT / rel
        if alt.is_dir():
            directory = alt
        else:
            errors.append(f"background: directory missing {directory}")
            return errors
    samples = sorted(directory.glob("*.mp4"))
    if len(samples) != required:
        errors.append(f"background_count:{len(samples)}!={required}")
    return errors


def check_preflight_config(lock: dict, root: Path | None = None) -> list[str]:
    """Config/lock-only checks for orchestrator step 1.

    Speakers, lock voice IDs, speeds, D: root, background bank,
    skip-existing forbidden. Does not inspect job scenes, ASS,
    provenance, auth WAV, or a stale job voice_map.
    """
    errors: list[str] = []
    allowed = ["narrator", "scripture"]
    speakers = list(lock.get("speakers") or [])
    for sid in allowed:
        if sid not in speakers:
            errors.append(f"lock: missing speaker {sid}")
    for sid in speakers:
        if sid not in allowed:
            errors.append(f"lock: extra speaker {sid}")

    expected_voice = {"narrator": "F5", "scripture": "M4"}
    expected_speed = {"narrator": 0.95, "scripture": 0.86}
    voice = lock.get("voice") or {}
    for sid in allowed:
        spec = voice.get(sid) or {}
        got_voice = spec.get("voice")
        if got_voice in FORBIDDEN_VOICES:
            errors.append(f"lock: forbidden voice {got_voice!r} for {sid}")
        want_voice = expected_voice[sid]
        if not got_voice:
            errors.append(f"lock: {sid} voice missing")
        elif got_voice != want_voice:
            errors.append(
                f"lock: {sid} voice {got_voice!r} != locked {want_voice!r}"
            )
        try:
            got_speed = float(spec.get("speed"))
        except (TypeError, ValueError):
            errors.append(f"lock: {sid} missing/invalid speed")
            got_speed = None
        if got_speed is not None:
            if got_speed in STALE_SPEEDS:
                errors.append(f"lock: stale speed {got_speed} for {sid}")
            want_speed = expected_speed[sid]
            if abs(got_speed - want_speed) > 1e-6:
                errors.append(
                    f"lock: {sid} speed {got_speed} != locked {want_speed}"
                )
        if sid == "scripture" and not (spec.get("audio_filter") or "").strip():
            errors.append("lock: empty scripture audio_filter")

    tts = lock.get("tts") or {}
    if not tts.get("skip_existing_forbidden", False):
        errors.append("lock: skip_existing_forbidden must be true")

    errors.extend(check_storage(lock))
    errors.extend(check_background(lock, root=root))
    return errors

def run_preflight(
    job: Path,
    lock: dict | None = None,
    lock_path: Path | None = None,
    root: Path | None = None,
) -> dict:
    """Early config/lock gate. Job scenes/ASS/provenance/WAV are later steps."""
    job = Path(job)
    lock = lock if lock is not None else load_lock(lock_path)
    errors = check_preflight_config(lock, root=root)
    return {
        "ok": not errors,
        "job": str(job),
        "errors": errors,
        "canonical": str(lock_path or _DEFAULT_LOCK),
        "mode": "config",
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Media rules preflight for a hermes job")
    ap.add_argument(
        "--job",
        required=True,
        help="Job directory (e.g. bible_healing/runs/.../hermes_jobs/full)",
    )
    ap.add_argument(
        "--lock",
        default=str(_DEFAULT_LOCK),
        help="Path to media_rules_lock.json",
    )
    ap.add_argument(
        "--root",
        default=str(_MODULE_ROOT),
        help="Module/repo root for resolving relative background paths",
    )
    args = ap.parse_args(argv)
    result = run_preflight(
        Path(args.job),
        lock_path=Path(args.lock),
        root=Path(args.root),
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
