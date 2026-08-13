# -*- coding: utf-8 -*-
"""Verify scene WAVs are sanitized, M4-locked, and safe to concat into authoritative audio."""
from __future__ import annotations

import argparse
import json
import re
import shutil
import sys
from pathlib import Path

SCENE_WAV_RE = re.compile(r"^scene_(\d+)\.wav$", re.IGNORECASE)
FORBIDDEN_PATH_FRAGMENTS = (
    "synced.mp4",
    "upload_package",
    "prelock",
    "audio_partial",
)
BACKUP_DIR_NAME = "audio_pre_sanitize_backup_20260813"
EMOTION_CHARS = "!?！？❗"


def list_scene_wavs(job: Path) -> list[Path]:
    """Return sorted scene_N.wav files at the job root only."""
    job = Path(job)
    found: list[tuple[int, Path]] = []
    for p in job.iterdir() if job.is_dir() else []:
        if not p.is_file():
            continue
        m = SCENE_WAV_RE.match(p.name)
        if m:
            found.append((int(m.group(1)), p))
    found.sort(key=lambda t: t[0])
    return [p for _, p in found]


def load_scenes(job: Path) -> list[dict]:
    path = Path(job) / "scenes.json"
    if not path.is_file():
        raise FileNotFoundError(f"missing scenes.json: {path}")
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, list):
        raise ValueError("scenes.json must be a list")
    return data


def load_provenance(job: Path) -> dict | None:
    path = Path(job) / "reports" / "tts_provenance.json"
    if not path.is_file():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def scene_speaker(scene: dict) -> str:
    meta = scene.get("meta") or {}
    if meta.get("speaker"):
        return str(meta["speaker"])
    segs = scene.get("segments") or []
    if segs and segs[0].get("speaker"):
        return str(segs[0]["speaker"])
    return "narrator"


def pieces_by_order(pieces: list[dict]) -> dict[int, list[dict]]:
    by: dict[int, list[dict]] = {}
    for piece in pieces:
        order = piece.get("scene_order")
        if order is None and piece.get("order") is not None:
            order = piece.get("order")
        if order is None:
            continue
        by.setdefault(int(order), []).append(piece)
    return by


def path_has_forbidden_fragment(path: Path | str) -> list[str]:
    s = str(path).replace("\\", "/").lower()
    hits = []
    for frag in FORBIDDEN_PATH_FRAGMENTS:
        if frag.lower() in s:
            hits.append(frag)
    return hits


def _check_piece(piece: dict, *, order: int, index: int) -> list[str]:
    errors: list[str] = []
    speaker = piece.get("speaker") or ""
    text = piece.get("text") or ""
    if any(ch in text for ch in EMOTION_CHARS):
        errors.append(
            f"scene_order={order} piece[{index}]: emotion punctuation remains in text (!/?)"
        )
    piece_path = piece.get("path") or ""
    for frag in path_has_forbidden_fragment(piece_path):
        errors.append(
            f"scene_order={order} piece[{index}]: forbidden path fragment {frag!r} in {piece_path}"
        )
    if speaker == "scripture":
        if piece.get("voice") != "M4":
            errors.append(
                f"scene_order={order} piece[{index}]: scripture voice "
                f"{piece.get('voice')!r} != M4"
            )
        if not piece.get("filter_applied"):
            errors.append(
                f"scene_order={order} piece[{index}]: scripture filter_applied is not true"
            )
    return errors


def verify_authoritative_audio(job: Path) -> dict:
    """
    Validate job-root scene_*.wav against scenes.json + reports/tts_provenance.json.

    Returns:
        {
          "ok": bool,
          "errors": list[str],
          "scene_count": int,
          "wav_count": int,
          "wavs": list[Path],  # only when ok (or best-effort ordered list when not)
          "job": str,
        }
    """
    job = Path(job)
    errors: list[str] = []

    for frag in path_has_forbidden_fragment(job):
        errors.append(f"job path contains forbidden fragment {frag!r}: {job}")

    try:
        scenes = load_scenes(job)
    except (OSError, ValueError, json.JSONDecodeError) as e:
        return {
            "ok": False,
            "errors": errors + [f"scenes.json error: {e}"],
            "scene_count": 0,
            "wav_count": 0,
            "wavs": [],
            "job": str(job),
        }

    scene_count = len(scenes)
    wavs = list_scene_wavs(job)
    wav_count = len(wavs)

    if wav_count != scene_count:
        errors.append(
            f"scene_*.wav count mismatch: found {wav_count} != scenes.json scene count {scene_count}"
        )

    # Expect contiguous scene_1 .. scene_N matching orders when possible
    orders = sorted(int(s.get("order") or (i + 1)) for i, s in enumerate(scenes))
    wav_orders = []
    for p in wavs:
        m = SCENE_WAV_RE.match(p.name)
        if m:
            wav_orders.append(int(m.group(1)))
    if scene_count and wav_orders and wav_orders != orders:
        # still allow if counts match but report missing numbers
        missing = [o for o in orders if o not in set(wav_orders)]
        extra = [o for o in wav_orders if o not in set(orders)]
        if missing:
            errors.append(f"missing scene wavs for orders: {missing}")
        if extra:
            errors.append(f"extra scene wavs not in scenes.json orders: {extra}")

    for p in wavs:
        for frag in path_has_forbidden_fragment(p):
            errors.append(f"wav path contains forbidden fragment {frag!r}: {p}")

    prov = load_provenance(job)
    if prov is None:
        errors.append("missing provenance: reports/tts_provenance.json")
        by_order: dict[int, list[dict]] = {}
    else:
        pieces = list(prov.get("pieces") or [])
        if not pieces:
            errors.append("missing provenance: reports/tts_provenance.json has no pieces")
        by_order = pieces_by_order(pieces)

    order_to_scene = {
        int(s.get("order") or (i + 1)): s for i, s in enumerate(scenes)
    }
    for order in orders:
        scene = order_to_scene.get(order) or {}
        sp = scene_speaker(scene)
        plist = by_order.get(order) or []
        if not plist:
            errors.append(f"missing provenance for scene_order={order} (scene_{order}.wav)")
            continue
        for idx, piece in enumerate(plist):
            errors.extend(_check_piece(piece, order=order, index=idx))
        # if scene is scripture, require at least one scripture piece
        if sp == "scripture":
            if not any((p.get("speaker") == "scripture") for p in plist):
                errors.append(
                    f"scene_order={order}: scene speaker is scripture but no scripture pieces"
                )

    ok = not errors
    return {
        "ok": ok,
        "errors": errors,
        "scene_count": scene_count,
        "wav_count": wav_count,
        "wavs": wavs if ok else wavs,
        "job": str(job),
    }


def find_unsanitized_scene_orders(job: Path) -> list[int]:
    """Scene orders whose provenance pieces fail M4/filter/no-emotion checks."""
    job = Path(job)
    prov = load_provenance(job)
    if prov is None:
        # without provenance every existing wav is suspect
        return [int(SCENE_WAV_RE.match(p.name).group(1)) for p in list_scene_wavs(job)]  # type: ignore[union-attr]
    by_order = pieces_by_order(list(prov.get("pieces") or []))
    bad: list[int] = []
    for order, plist in sorted(by_order.items()):
        piece_errors: list[str] = []
        for idx, piece in enumerate(plist):
            piece_errors.extend(_check_piece(piece, order=order, index=idx))
        if piece_errors or not plist:
            bad.append(int(order))
    # also missing files known as scene wavs without pieces?
    for p in list_scene_wavs(job):
        m = SCENE_WAV_RE.match(p.name)
        if not m:
            continue
        order = int(m.group(1))
        if order not in by_order and order not in bad:
            bad.append(order)
    return sorted(set(bad))


def backup_unsanitized_wavs(
    job: Path,
    scene_orders: list[int] | None = None,
    *,
    dry_run: bool = False,
    backup_name: str = BACKUP_DIR_NAME,
) -> list[dict]:
    """
    Move rejected/unsanitized scene_N.wav into job/<backup_name>/.

    dry_run defaults to False (actually moves). Prefer dry_run=True or tmp fixtures
    before touching production WAVs.
    """
    job = Path(job)
    orders = list(scene_orders) if scene_orders is not None else find_unsanitized_scene_orders(job)
    backup_dir = job / backup_name
    results: list[dict] = []
    if not dry_run:
        backup_dir.mkdir(parents=True, exist_ok=True)
    for order in orders:
        src = job / f"scene_{order}.wav"
        dest = backup_dir / f"scene_{order}.wav"
        rec = {
            "order": order,
            "src": str(src),
            "dest": str(dest),
            "dry_run": bool(dry_run),
            "moved": False,
            "exists": src.is_file(),
        }
        if not src.is_file():
            rec["error"] = "source missing"
            results.append(rec)
            continue
        if dry_run:
            results.append(rec)
            continue
        # avoid clobber: if dest exists, add suffix
        final_dest = dest
        if final_dest.exists():
            final_dest = backup_dir / f"scene_{order}_{src.stat().st_mtime_ns}.wav"
            rec["dest"] = str(final_dest)
        shutil.move(str(src), str(final_dest))
        rec["moved"] = True
        results.append(rec)
    return results


def main(argv: list[str] | None = None) -> None:
    ap = argparse.ArgumentParser(
        description="Verify scene WAVs are sanitized M4 authoritative sources"
    )
    ap.add_argument("--job", required=True, help="Hermes job directory with scenes.json + scene_*.wav")
    ap.add_argument(
        "--backup-unsanitized",
        action="store_true",
        help=f"Move unsanitized scene_*.wav to {BACKUP_DIR_NAME}/",
    )
    ap.add_argument(
        "--dry-run",
        action="store_true",
        help="With --backup-unsanitized, only report moves",
    )
    args = ap.parse_args(argv)
    job = Path(args.job)
    if args.backup_unsanitized:
        moved = backup_unsanitized_wavs(job, dry_run=bool(args.dry_run))
        print(json.dumps({"backup": moved}, ensure_ascii=False, indent=2))
    result = verify_authoritative_audio(job)
    # Paths are not JSON-serializable
    out = {
        "ok": result["ok"],
        "errors": result["errors"],
        "scene_count": result["scene_count"],
        "wav_count": result["wav_count"],
        "wavs": [str(p) for p in result["wavs"]],
        "job": result["job"],
    }
    print(json.dumps(out, ensure_ascii=False, indent=2))
    if not result["ok"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
