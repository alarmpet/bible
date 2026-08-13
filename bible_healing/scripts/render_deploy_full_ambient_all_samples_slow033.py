from pathlib import Path
import subprocess

R=Path(r"C:\Users\amd\module")
J=R/"bible_healing/runs/ep01_anxious_night/hermes_jobs/full"
BGDIR=R/"bible_healing/assets/movie-sample/pingpong-1min"
SRC=R/"bible_healing/runs/ep01_anxious_night/upload_package/final-ep01-full.mp4"
ASS=J/"subtitles-timed-ko.ass"
FF=Path(r"C:\Users\amd\hermes\node_modules\ffmpeg-static\ffmpeg.exe")
FP=Path(r"C:\Users\amd\hermes\node_modules\@ffprobe-installer\win32-x64\ffprobe.exe")
OUT=J/"deploy-ep01-full-ambient-all-samples-slow033-with-subtitles.mp4"
W=J/"deploy_all_samples_slow033"; W.mkdir(exist_ok=True)
def run(c): subprocess.run(c,check=True)
dur=float(subprocess.check_output([str(FP),"-v","error","-show_entries","format=duration","-of","default=nw=1:nk=1",str(SRC)],text=True).strip())
samples=sorted(BGDIR.glob("*.mp4"))
if len(samples)<2: raise SystemExit("Need all ambient samples")
lst=W/"background_all_samples_loop.txt"; rows=[]
for _ in range(5):
    for p in samples: rows.append(f"file '{p.as_posix()}'")
lst.write_text("\n".join(rows),encoding="utf-8")
ass=str(ASS).replace("\\","/").replace(":","\\:")
vf=f"setpts=3*PTS,trim=duration={dur:.3f},subtitles='{ass}'"
run([str(FF),"-y","-hide_banner","-loglevel","error","-f","concat","-safe","0","-i",str(lst),"-i",str(SRC),"-vf",vf,"-t",str(dur),"-map","0:v:0","-map","1:a:0","-c:v","libx264","-preset","ultrafast","-crf","30","-pix_fmt","yuv420p","-c:a","copy","-movflags","+faststart",str(OUT)])
print({"output":str(OUT),"duration":dur,"background_samples":len(samples),"background_speed":0.333,"subtitles":True,"source_audio":str(SRC)})
