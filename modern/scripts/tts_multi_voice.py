# -*- coding: utf-8 -*-
"""
Multi-voice SuperTonic3 TTS for Hermes jobs.

- Reads scenes.json (segments with speaker) + voice_map.json
- Synthesizes each segment with distinct voice/speed
- Concatenates to scene_{order}.wav at job root (Hermes render contract)

Usage:
  python tts_multi_voice.py --job <jobDir> --preview-only   # sample lines only
  python tts_multi_voice.py --job <jobDir>
  python tts_multi_voice.py --job <jobDir> --skip-existing

Requires: SuperTonic venv python or HERMES_TTS_PYTHON, engine on TTS_ROOT/src
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import re
from pathlib import Path

from paths import FFMPEG, FFPROBE, TTS_PYTHON, TTS_ROOT

_BH_SCRIPTS = Path(__file__).resolve().parents[2] / "bible_healing" / "scripts"
if str(_BH_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_BH_SCRIPTS))

from apply_audio_filter import apply_scripture_filter  # noqa: E402
from sanitize_script import assert_no_emotion_triggers  # noqa: E402
from verify_voice_provenance import (  # noqa: E402
    build_piece_provenance,
    enforce_skip_existing,
    is_bible_scripture_job,
    load_media_lock,
    prepare_preview_request,
    prepare_speech_units,
    resolve_total_step,
    run_job_preflight,
    verify_tts_provenance,
    write_tts_provenance,
)

def clean_for_tts(text: str) -> str:
    text = re.sub(r"\([^()]*\)|（[^（）]*）", " ", text or "")
    text = text.replace("!", ".").replace("！", ".")
    return re.sub(r"\s+", " ", text).strip()


def load_engine(job_dir: Path):
    sys.path.insert(0, str(TTS_ROOT / "src"))
    from supertonic3_engine import Supertonic3Engine  # type: ignore

    return Supertonic3Engine(output_dir=job_dir)


def ffmpeg_bin() -> str:
    if FFMPEG.exists():
        return str(FFMPEG)
    return os.environ.get("FFMPEG_BIN") or "ffmpeg"


def ffprobe_bin() -> str:
    if FFPROBE.exists():
        return str(FFPROBE)
    # sibling of ffmpeg-static sometimes
    sibling = FFMPEG.parent / "ffprobe.exe"
    if sibling.exists():
        return str(sibling)
    return os.environ.get("FFPROBE_BIN") or "ffprobe"


def concat_wavs(paths: list[Path], out: Path, gap_sec: float = 0.1) -> bool:
    """Concat wavs with optional silence using ffmpeg."""
    import shutil

    if not paths:
        return False
    if len(paths) == 1:
        shutil.copy2(paths[0], out)
        return out.exists() and out.stat().st_size > 0
    ff = ffmpeg_bin()
    # re-encode concat is more reliable across slightly different wav headers
    # filter_complex amix alternative: concat demuxer with regenerated silence
    sil = out.parent / "_sil.wav"
    subprocess.run(
        [ff, "-y", "-f", "lavfi", "-i", "anullsrc=r=24000:cl=mono", "-t", str(gap_sec), str(sil)],
        capture_output=True,
    )
    lst = out.parent / "_concat_list.txt"
    lines = []
    for i, p in enumerate(paths):
        lines.append(f"file '{p.resolve().as_posix()}'")
        if i < len(paths) - 1 and sil.exists():
            lines.append(f"file '{sil.resolve().as_posix()}'")
    lst.write_text("\n".join(lines), encoding="utf-8")
    res = subprocess.run(
        [ff, "-y", "-f", "concat", "-safe", "0", "-i", str(lst), "-c:a", "pcm_s16le", str(out)],
        capture_output=True,
    )
    if sil.exists():
        sil.unlink(missing_ok=True)
    lst.unlink(missing_ok=True)
    if res.returncode != 0:
        return False
    return out.exists() and out.stat().st_size > 0


def probe_duration(wav: Path) -> float:
    cmd = [
        ffprobe_bin(),
        "-v",
        "error",
        "-show_entries",
        "format=duration",
        "-of",
        "default=noprint_wrappers=1:nokey=1",
        str(wav),
    ]
    try:
        r = subprocess.run(cmd, capture_output=True, text=True)
        if r.returncode == 0 and r.stdout.strip():
            return float(r.stdout.strip())
    except Exception:
        pass
    # fallback: non-zero file size counts as success with unknown duration
    if wav.exists() and wav.stat().st_size > 1000:
        return -1.0  # unknown but present
    return 0.0


def preview_only(engine, vm: dict, job: Path) -> dict:
    samples = vm.get("sample_lines") or {}
    speakers = vm.get("speakers") or {}
    lock = load_media_lock() if is_bible_scripture_job(speakers) else None
    out_dir = job / "voice_previews"
    out_dir.mkdir(exist_ok=True)
    results = []
    for sid, line in samples.items():
        conf = speakers.get(sid) or {}
        req = prepare_preview_request(sid, line, conf, lock=lock, speakers=speakers)
        voice = req["voice"]
        path = out_dir / f"preview_{sid}_{voice}.wav"
        raw_path = out_dir / f"preview_{sid}_{voice}.raw.wav" if req["apply_filter"] else path
        info = engine.synthesize_to_file(
            text=req["text"],
            output_path=raw_path,
            voice=voice,
            lang="ko",
            speed=req["speed"],
            total_step=int(req["total_step"]),
            silence_duration=float(req["silence_duration"]),
            max_chunk_length=int(req["max_chunk"]),
            verbose=False,
        )
        if req["apply_filter"]:
            apply_scripture_filter(raw_path, path)
            if raw_path != path and raw_path.exists():
                raw_path.unlink(missing_ok=True)
        results.append(
            {
                "speaker": sid,
                "voice": voice,
                "path": str(path),
                "duration": info.get("duration"),
                "text": req["text"],
                "total_step": req["total_step"],
                "filter_applied": req["apply_filter"],
            }
        )
        print(f"preview {sid} {voice} -> {path.name}")
    report = {"ok": True, "previews": results}
    (job / "reports" / "tts_preview_report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return report


def run_job(job: Path, skip_existing: bool) -> dict:
    lock = run_job_preflight(job, skip_existing)
    bible = lock is not None
    scenes = json.loads((job / "scenes.json").read_text(encoding="utf-8"))
    vm = json.loads((job / "voice_map.json").read_text(encoding="utf-8"))
    speakers = vm["speakers"]
    # distinct check
    narr_v = speakers["narrator"]["voice"]
    for sid, c in speakers.items():
        if sid != "narrator" and c.get("voice") == narr_v:
            raise SystemExit(f"VOICE_MAP_DISTINCT fail: narrator={narr_v} used by {sid}")

    engine = load_engine(job)
    seg_dir = job / "segments"
    seg_dir.mkdir(exist_ok=True)
    items = []
    pieces = []
    ok = True

    for sc in scenes:
        order = int(sc["order"])
        scene_wav = job / f"scene_{order}.wav"
        if skip_existing and not bible and scene_wav.exists() and scene_wav.stat().st_size > 0:
            items.append({"order": order, "path": str(scene_wav), "skipped": True, "duration": probe_duration(scene_wav)})
            continue
        segs = sc.get("segments") or [{"speaker": "narrator", "text": sc.get("narration") or "", "seg_id": f"{sc.get('scene_id')}_01"}]
        seg_paths = []
        seg_meta = []
        for seg in segs:
            sid = seg.get("speaker") or "narrator"
            conf = speakers.get(sid) or speakers["narrator"]
            if bible:
                try:
                    units = prepare_speech_units(seg.get("text") or "", sid, lock)
                except ValueError as e:
                    ok = False
                    seg_meta.append({"seg_id": seg.get("seg_id"), "error": str(e), "speaker": sid})
                    print(f"FAIL order={order} seg={seg.get('seg_id')}: {e}")
                    continue
                voice_spec = (lock.get("voice") or {}).get(sid) or {}
                voice = voice_spec.get("voice") or conf["voice"]
                speed = float(voice_spec.get("speed") or conf.get("speed") or 1.05)
                total_step = resolve_total_step(sid, lock)
                if sid == "scripture":
                    max_chunk = int(voice_spec.get("max_chunk_length") or 90)
                    silence = float(voice_spec.get("silence_seconds") or conf.get("silence_duration") or 0.65)
                else:
                    max_chunk = int(conf.get("max_chunk_length") or 130)
                    silence = float(voice_spec.get("silence_seconds") or conf.get("silence_duration") or 0.24)
            else:
                text = clean_for_tts(seg.get("text") or "")
                if not text:
                    continue
                units = [text]
                voice = conf["voice"]
                speed = float(conf.get("speed") or 1.05)
                total_step = int(conf.get("total_step") or 8)
                max_chunk = int(conf.get("max_chunk_length") or 130)
                silence = float(conf.get("silence_duration") or 0.12)
            for ui, unit in enumerate(units):
                if bible:
                    assert_no_emotion_triggers(unit)
                stem = f"{seg.get('seg_id', f'o{order}')}_{sid}_{voice}_{ui:02d}"
                spath = seg_dir / f"{stem}.wav"
                raw_path = seg_dir / f"{stem}.raw.wav" if bible and sid == "scripture" else spath
                try:
                    info = engine.synthesize_to_file(
                        text=unit,
                        output_path=raw_path,
                        voice=voice,
                        lang="ko",
                        speed=speed,
                        total_step=total_step,
                        silence_duration=silence,
                        max_chunk_length=int(max_chunk),
                        verbose=False,
                    )
                    filter_applied = False
                    if bible and sid == "scripture":
                        apply_scripture_filter(
                            raw_path,
                            spath,
                            pitch_percent=float(voice_spec.get("pitch", -14)),
                        )
                        filter_applied = True
                        if raw_path != spath and raw_path.exists():
                            raw_path.unlink(missing_ok=True)
                    probed = probe_duration(spath)
                    piece_dur = probed if probed and probed > 0 else info.get("duration")
                    piece = build_piece_provenance(
                        speaker=sid,
                        voice=voice,
                        speed=speed,
                        total_step=total_step,
                        max_chunk=max_chunk,
                        text=unit,
                        wav_path=spath,
                        filter_applied=filter_applied,
                        scene_order=order,
                        scene_id=sc.get("scene_id"),
                        seg_id=seg.get("seg_id"),
                        unit_index=ui,
                        path=str(spath),
                        duration=piece_dur,
                    )
                    pieces.append(piece)
                    seg_paths.append(spath)
                    seg_meta.append(
                        {
                            "seg_id": seg.get("seg_id"),
                            "unit_index": ui,
                            "speaker": sid,
                            "voice": voice,
                            "speed": speed,
                            "total_step": total_step,
                            "max_chunk": max_chunk,
                            "path": str(spath),
                            "duration": info.get("duration"),
                            "text_len": len(unit),
                            "filter_applied": filter_applied,
                        }
                    )
                except Exception as e:
                    ok = False
                    seg_meta.append({"seg_id": seg.get("seg_id"), "unit_index": ui, "error": str(e), "speaker": sid})
                    print(f"FAIL order={order} seg={seg.get('seg_id')} unit={ui}: {e}")

        if not seg_paths:
            ok = False
            items.append({"order": order, "ok": False, "error": "no segments"})
            continue
        speakers_in = [(seg.get("speaker") or "narrator") for seg in (sc.get("segments") or segs)]
        if bible and any(s == "scripture" for s in speakers_in):
            gap = float((lock.get("voice") or {}).get("scripture", {}).get("silence_seconds") or 0.65)
        else:
            gap = 0.1
        if not concat_wavs(seg_paths, scene_wav, gap_sec=gap):
            ok = False
            items.append(
                {
                    "order": order,
                    "scene_id": sc.get("scene_id"),
                    "ok": False,
                    "error": "concat_wavs_failed",
                }
            )
            print(f"FAIL order={order}: concat_wavs failed for {len(seg_paths)} pieces")
            continue
        dur = probe_duration(scene_wav)
        size_ok = scene_wav.exists() and scene_wav.stat().st_size > 1000
        # dur==-1 means probe unavailable but file present
        item_ok = size_ok and (dur > 0 or dur == -1)
        if not item_ok:
            ok = False
        items.append(
            {
                "order": order,
                "scene_id": sc.get("scene_id"),
                "path": str(scene_wav),
                "duration": dur if dur > 0 else None,
                "segments": seg_meta,
                "ok": item_ok,
            }
        )
        print(f"scene {order}: segs={len(seg_paths)} dur={dur} size={scene_wav.stat().st_size} -> {scene_wav.name}")

    report = {
        "ok": ok and all(i.get("ok", True) for i in items if "ok" in i),
        "engine": "supertonic3",
        "tts_root": str(TTS_ROOT),
        "tts_python": str(TTS_PYTHON),
        "scene_count": len(scenes),
        "items": items,
    }
    # strict: any fail => ok false
    if any(i.get("ok") is False for i in items):
        report["ok"] = False
    (job / "reports").mkdir(exist_ok=True)
    if bible:
        write_tts_provenance(
            job,
            pieces,
            extra={"tts_root": str(TTS_ROOT), "scene_count": len(scenes), "ok": report["ok"]},
        )
        if pieces:
            verify_tts_provenance(job / "reports" / "tts_provenance.json")
    (job / "scene_audio_manifest.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    (job / "reports" / "tts_report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print("tts ok=" + str(report["ok"]))
    if not report["ok"]:
        raise SystemExit(1)
    return report


def ensure_tts_python():
    """Re-exec under SuperTonic venv if current interpreter lacks `supertonic`."""
    try:
        import supertonic  # noqa: F401
        return
    except Exception:
        pass
    py = TTS_PYTHON
    if not py.exists():
        raise SystemExit(
            f"supertonic not installed in current Python, and TTS venv missing: {py}\n"
            f"Run with: {py} scripts/tts_multi_voice.py ..."
        )
    if Path(sys.executable).resolve() == py.resolve():
        raise SystemExit("supertonic missing inside TTS venv — reinstall SuperTonic requirements")
    os.execv(str(py), [str(py), str(Path(__file__).resolve()), *sys.argv[1:]])


def main():
    ensure_tts_python()
    ap = argparse.ArgumentParser()
    ap.add_argument("--job", required=True)
    ap.add_argument("--preview-only", action="store_true")
    ap.add_argument("--skip-existing", action="store_true")
    args = ap.parse_args()
    job = Path(args.job)
    (job / "reports").mkdir(exist_ok=True)
    vm = json.loads((job / "voice_map.json").read_text(encoding="utf-8"))
    speakers = vm.get("speakers") or {}
    if is_bible_scripture_job(speakers):
        enforce_skip_existing(args.skip_existing)
    if not args.preview_only:
        run_job(job, args.skip_existing)
        return
    engine = load_engine(job)
    preview_only(engine, vm, job)


if __name__ == "__main__":
    main()
