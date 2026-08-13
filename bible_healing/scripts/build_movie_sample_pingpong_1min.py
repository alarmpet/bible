from pathlib import Path
import subprocess

FF = Path(r"C:\Users\amd\hermes\node_modules\ffmpeg-static\ffmpeg.exe")
SRC_DIR = Path(r"C:\Users\amd\module\bible_healing\assets\movie-sample")
OUT_DIR = SRC_DIR / "pingpong-1min"

def run(cmd):
    subprocess.run(cmd, check=True)

def make_one(src: Path):
    stem = src.stem
    work = OUT_DIR / f".work_{stem}"
    work.mkdir(parents=True, exist_ok=True)
    rev = work / "reverse.mp4"
    cycle = work / "cycle.mp4"
    out = OUT_DIR / f"{stem}_pingpong_1min.mp4"

    run([str(FF), "-y", "-hide_banner", "-loglevel", "error", "-i", str(src),
         "-an", "-vf", "reverse", "-c:v", "libx264", "-preset", "ultrafast",
         "-crf", "23", "-pix_fmt", "yuv420p", str(rev)])
    run([str(FF), "-y", "-hide_banner", "-loglevel", "error", "-i", str(src), "-i", str(rev),
         "-filter_complex", "[0:v][1:v]concat=n=2:v=1:a=0,setpts=N/FRAME_RATE/TB[v]",
         "-map", "[v]", "-an", "-c:v", "libx264", "-preset", "ultrafast", "-crf", "23",
         "-pix_fmt", "yuv420p", str(cycle)])
    run([str(FF), "-y", "-hide_banner", "-loglevel", "error", "-stream_loop", "-1", "-i", str(cycle),
         "-t", "60", "-an", "-c:v", "libx264", "-preset", "medium", "-crf", "20",
         "-pix_fmt", "yuv420p", "-movflags", "+faststart", str(out)])
    return out

def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    files = sorted(SRC_DIR.glob("*.mp4"))
    results = []
    for src in files:
        results.append(str(make_one(src)))
    print({"count": len(results), "duration_sec_each": 60, "outputs": results})

if __name__ == "__main__":
    main()
