# -*- coding: utf-8 -*-
"""Assemble v3 motion clips with the existing audio/subtitle master into a candidate."""
from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path


def render_pilot(source_build: Path, pilot_dir: Path) -> Path:
    source_build = Path(source_build).resolve()
    pilot_dir = Path(pilot_dir).resolve()
    clips = sorted((pilot_dir / "motion_clips").glob("*_motion.mp4"))
    if not clips or any(p.stat().st_size == 0 for p in clips):
        raise RuntimeError("motion clips are incomplete or contain zero-byte files")
    concat = pilot_dir / "motion_concat.txt"
    concat.write_text("\n".join(f"file '{p.as_posix()}'" for p in clips), encoding="utf-8")
    visual = pilot_dir / "visual_master.mp4"
    subprocess.run(["ffmpeg", "-y", "-hide_banner", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", str(concat), "-c", "copy", str(visual)], check=True)
    candidate = pilot_dir / "candidate" / "HA002-pilot-v4-001.mp4"
    candidate.parent.mkdir(parents=True, exist_ok=True)
    ass = str(source_build / "subtitles.ass").replace("\\", "/").replace(":", "\\:")
    subprocess.run(["ffmpeg", "-y", "-hide_banner", "-loglevel", "error", "-i", str(visual), "-i", str(source_build / "master_audio_48k.wav"), "-vf", f"subtitles='{ass}'", "-c:v", "libx264", "-preset", "fast", "-crf", "18", "-x264-params", "colorprim=bt709:transfer=bt709:colormatrix=bt709", "-pix_fmt", "yuv420p", "-colorspace", "bt709", "-color_primaries", "bt709", "-color_trc", "bt709", "-color_range", "tv", "-c:a", "aac", "-b:a", "192k", "-af", "volume=-0.5dB", "-shortest", "-movflags", "+faststart", str(candidate)], check=True)
    return candidate


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-build", type=Path, required=True)
    parser.add_argument("--pilot-dir", type=Path, required=True)
    args = parser.parse_args()
    print(render_pilot(args.source_build, args.pilot_dir))
