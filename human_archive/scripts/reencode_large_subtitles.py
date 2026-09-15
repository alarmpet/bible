# -*- coding: utf-8 -*-
"""Burn a larger, consistent ASS subtitle style into an existing visual master."""
from __future__ import annotations

import argparse
import re
import subprocess
from pathlib import Path


def reencode(input_video: Path, audio: Path, subtitles: Path, output: Path, font_size: int = 72, outline: float = 5.0) -> Path:
    output.parent.mkdir(parents=True, exist_ok=True)
    text = subtitles.read_text(encoding="utf-8-sig")
    text = re.sub(r"(?m)^Style: DocuMain,([^,]+),54,", rf"Style: DocuMain,\1,{font_size},", text)
    text = re.sub(r"(?m)^Style: DocuMain,(.*?,\d+,[^\n]*?,)4\.5,2\.0,", lambda m: f"Style: DocuMain,{m.group(1)}{outline},2.0,", text)
    ass_copy = output.with_suffix(".large.ass")
    ass_copy.write_text(text, encoding="utf-8")
    ass = str(ass_copy).replace("\\", "/").replace(":", "\\:")
    subprocess.run([
        "ffmpeg", "-y", "-hide_banner", "-loglevel", "error", "-i", str(input_video), "-i", str(audio),
        "-vf", f"subtitles='{ass}'", "-c:v", "libx264", "-preset", "fast", "-crf", "18",
        "-x264-params", "colorprim=bt709:transfer=bt709:colormatrix=bt709", "-pix_fmt", "yuv420p",
        "-colorspace", "bt709", "-color_primaries", "bt709", "-color_trc", "bt709", "-color_range", "tv",
        "-c:a", "aac", "-b:a", "192k", "-af", "volume=-0.5dB", "-shortest", "-movflags", "+faststart", str(output)
    ], check=True)
    return output


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--audio", type=Path, required=True)
    parser.add_argument("--subtitles", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--font-size", type=int, default=72)
    args = parser.parse_args()
    print(reencode(args.input, args.audio, args.subtitles, args.output, args.font_size))
