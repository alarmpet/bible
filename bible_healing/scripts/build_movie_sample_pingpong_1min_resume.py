from pathlib import Path
import subprocess

FF=Path(r"C:\Users\amd\hermes\node_modules\ffmpeg-static\ffmpeg.exe")
SRC=Path(r"C:\Users\amd\module\bible_healing\assets\movie-sample")
OUT=SRC/"pingpong-1min"; OUT.mkdir(exist_ok=True)

def duration(p):
    fp=Path(r"C:\Users\amd\hermes\node_modules\@ffprobe-installer\win32-x64\ffprobe.exe")
    try: return float(subprocess.check_output([str(fp),"-v","error","-show_entries","format=duration","-of","default=nw=1:nk=1",str(p)],text=True).strip())
    except: return 0

for src in sorted(SRC.glob("*.mp4")):
    out=OUT/f"{src.stem}_pingpong_1min.mp4"
    if duration(out) >= 59.9: continue
    work=OUT/f".resume_{src.stem}"; work.mkdir(exist_ok=True)
    rev=work/"reverse.mp4"; cycle=work/"cycle.mp4"
    subprocess.run([str(FF),"-y","-hide_banner","-loglevel","error","-i",str(src),"-an","-vf","reverse","-c:v","libx264","-preset","ultrafast","-crf","23","-pix_fmt","yuv420p",str(rev)],check=True)
    subprocess.run([str(FF),"-y","-hide_banner","-loglevel","error","-i",str(src),"-i",str(rev),"-filter_complex","[0:v][1:v]concat=n=2:v=1:a=0,setpts=N/FRAME_RATE/TB[v]","-map","[v]","-an","-c:v","libx264","-preset","ultrafast","-crf","23","-pix_fmt","yuv420p",str(cycle)],check=True)
    subprocess.run([str(FF),"-y","-hide_banner","-loglevel","error","-stream_loop","-1","-i",str(cycle),"-t","60","-an","-c:v","libx264","-preset","ultrafast","-crf","23","-pix_fmt","yuv420p","-movflags","+faststart",str(out)],check=True)
    print(out)
