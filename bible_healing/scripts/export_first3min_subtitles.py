from pathlib import Path
import json, subprocess

ROOT=Path(r"C:\Users\amd\module")
JOB=ROOT/"bible_healing/runs/ep01_anxious_night/hermes_jobs/actual_first3min_locked_M4"
WAVS=JOB/"render_work"
OUT=JOB/"subtitles-first3min-actual.srt"
FP=Path(r"C:\Users\amd\hermes\node_modules\@ffprobe-installer\win32-x64\ffprobe.exe")

def probe(p):
    return float(subprocess.check_output([str(FP),"-v","error","-show_entries","format=duration","-of","default=nw=1:nk=1",str(p)],text=True).strip())
def ts(v):
    h=int(v//3600); m=int((v%3600)//60); s=v%60; ms=int(round((s-int(s))*1000)); s=int(s)
    if ms>=1000: s+=1; ms=0
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"

scenes=json.loads((JOB/"scenes.json").read_text(encoding="utf-8"))
t=0.0; rows=[]
for i,s in enumerate(scenes):
    if t>=180: break
    d=probe(WAVS/f"scene_{i+1}_low.wav"); e=min(t+d,180)
    text=(s.get("narration") or "").replace("\n"," ").strip()
    rows.append(f"{len(rows)+1}\n{ts(t)} --> {ts(e)}\n{text}\n")
    t=e
OUT.write_text("\n".join(rows),encoding="utf-8-sig")
print({"path":str(OUT),"cues":len(rows),"duration":t})
