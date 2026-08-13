"""Render a short, deliberately subtle candle-ambient proof clip.

This is a diagnostic renderer, not the final long-form renderer.  It keeps the
source plate recognizable while adding slow camera breathing, low-frequency
warmth variation, and a very soft blurred light layer.  The output is useful
for reviewing whether the visual is alive without becoming distracting.
"""
from __future__ import annotations

import argparse
import subprocess
from pathlib import Path


FFMPEG = Path(r"C:\Users\amd\hermes\node_modules\ffmpeg-static\ffmpeg.exe")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--image", required=True)
    ap.add_argument("--audio", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--duration", type=float, default=60.0)
    args = ap.parse_args()

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    # 30fps, restrained 1.5% push-in, plus a blurred duplicate whose opacity
    # breathes over 9 seconds.  The effect is intentionally below slideshow
    # territory: no cuts, flashes, particles, or artificial camera shake.
    vf = (
        "split=2[base][glow];"
        "[base]scale=iw*1.02:ih*1.02,"
        "zoompan=z='1.0+0.012*sin(2*PI*on/(30*18))':"
        "x='(iw-iw/zoom)/2':y='(ih-ih/zoom)/2':"
        "d=1:s=1920x1080:fps=30,"
        "eq=brightness='0.004*sin(2*PI*t/11)':"
        "saturation=1.02[baseout];"
        "[glow]scale=1920:1080,gblur=sigma=20,"
        "eq=brightness='0.01+0.008*sin(2*PI*t/9)',"
        "colorchannelmixer=rr=1.05:gg=0.92:bb=0.78:aa=0.10[glowout];"
        "[baseout][glowout]blend=all_mode=screen:all_opacity=0.18,format=yuv420p"
    )
    cmd = [
        str(FFMPEG), "-y", "-hide_banner", "-loglevel", "error",
        "-loop", "1", "-i", args.image, "-i", args.audio,
        "-t", str(args.duration), "-vf", vf,
        "-map", "0:v:0", "-map", "1:a:0", "-shortest",
        "-c:v", "libx264", "-preset", "medium", "-crf", "18",
        "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", str(out),
    ]
    subprocess.run(cmd, check=True)
    print(out)


if __name__ == "__main__":
    main()
