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
        # last resort: copy first segment
        shutil.copy2(paths[0], out)
        return out.exists()
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
    out_dir = job / "voice_previews"
    out_dir.mkdir(exist_ok=True)
    results = []
    for sid, line in samples.items():
        conf = speakers.get(sid) or {}
        voice = conf.get("voice") or "M1"
        speed = float(conf.get("speed") or 1.05)
        path = out_dir / f"preview_{sid}_{voice}.wav"
        info = engine.synthesize_to_file(
            text=line,
            output_path=path,
            voice=voice,
            lang="ko",
            speed=speed,
            total_step=int(conf.get("total_step") or 8),
            silence_duration=0.15,
            verbose=False,
        )
        results.append({"speaker": sid, "voice": voice, "path": str(path), "duration": info.get("duration")})
        print(f"preview {sid} {voice} -> {path.name}")
    report = {"ok": True, "previews": results}
    (job / "reports" / "tts_preview_report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return report


def run_job(job: Path, skip_existing: bool) -> dict:
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
    ok = True

    for sc in scenes:
        order = int(sc["order"])
        scene_wav = job / f"scene_{order}.wav"
        if skip_existing and scene_wav.exists() and scene_wav.stat().st_size > 0:
            items.append({"order": order, "path": str(scene_wav), "skipped": True, "duration": probe_duration(scene_wav)})
            continue
        segs = sc.get("segments") or [{"speaker": "narrator", "text": sc.get("narration") or "", "seg_id": f"{sc.get('scene_id')}_01"}]
        seg_paths = []
        seg_meta = []
        for seg in segs:
            text = clean_for_tts(seg.get("text") or "")
            if not text:
                continue
            sid = seg.get("speaker") or "narrator"
            conf = speakers.get(sid) or speakers["narrator"]
            voice = conf["voice"]
            speed = float(conf.get("speed") or 1.05)
            # Prefer short semantic units (e.g. bible verse expand) so max_chunk does not mid-cut.
            max_chunk = conf.get("max_chunk_length")
            if max_chunk is None:
                max_chunk = 130
            spath = seg_dir / f"{seg.get('seg_id', f'o{order}')}_{sid}_{voice}.wav"
            try:
                info = engine.synthesize_to_file(
                    text=text,
                    output_path=spath,
                    voice=voice,
                    lang="ko",
                    speed=speed,
                    total_step=int(conf.get("total_step") or 8),
                    silence_duration=float(conf.get("silence_duration") or 0.12),
                    max_chunk_length=int(max_chunk),
                    verbose=False,
                )
                seg_paths.append(spath)
                seg_meta.append(
                    {
                        "seg_id": seg.get("seg_id"),
                        "speaker": sid,
                        "voice": voice,
                        "speed": speed,
                        "path": str(spath),
                        "duration": info.get("duration"),
                        "text_len": len(text),
                    }
                )
            except Exception as e:
                ok = False
                seg_meta.append({"seg_id": seg.get("seg_id"), "error": str(e), "speaker": sid})
                print(f"FAIL order={order} seg={seg.get('seg_id')}: {e}")

        if not seg_paths:
            ok = False
            items.append({"order": order, "ok": False, "error": "no segments"})
            continue
        # gap: slightly longer for multi-unit scripture (verse-by-verse)
        speakers_in = [(seg.get("speaker") or "narrator") for seg in (sc.get("segments") or [])]
        gap = 0.22 if (len(seg_paths) > 1 and any(s == "scripture" for s in speakers_in)) else 0.1
        if not concat_wavs(seg_paths, scene_wav, gap_sec=gap):
            # fallback: copy first
            scene_wav.write_bytes(seg_paths[0].read_bytes())
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
    engine = load_engine(job)
    if args.preview_only:
        preview_only(engine, vm, job)
        return
    run_job(job, args.skip_existing)


if __name__ == "__main__":
    main()
