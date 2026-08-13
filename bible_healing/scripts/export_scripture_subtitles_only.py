from pathlib import Path
import json, re, subprocess

ROOT=Path(r"C:\Users\amd\module")
JOB=ROOT/"bible_healing/runs/ep01_anxious_night/hermes_jobs/actual_first3min_locked_M4"
OUT=JOB/"subtitles-scripture-section-only.srt"
FP=Path(r"C:\Users\amd\hermes\node_modules\@ffprobe-installer\win32-x64\ffprobe.exe")
def probe(p): return float(subprocess.check_output([str(FP),"-v","error","-show_entries","format=duration","-of","default=nw=1:nk=1",str(p)],text=True).strip())
def ts(v):
    h=int(v//3600); m=int((v%3600)//60); s=v%60; ms=int(round((s-int(s))*1000)); s=int(s)
    if ms>=1000: s+=1; ms=0
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"
scenes=json.loads((JOB/"scenes.json").read_text(encoding="utf-8"))
start=sum(probe(JOB/"render_work"/f"scene_{i}_low.wav") for i in range(1,5))
dur=probe(JOB/"render_work"/"scene_5_low.wav")
text=scenes[4].get("narration","").replace("\n"," ").strip()
parts=[x.strip() for x in re.split(r"(?<=[.!?。！？])\s*",text) if x.strip()]
weights=[max(1,len(x)) for x in parts]; total=sum(weights); rows=[]; t=start
for i,(p,w) in enumerate(zip(parts,weights),1):
    e=start+dur*(sum(weights[:i])/total)
    rows.append(f"{i}\n{ts(t)} --> {ts(e)}\n{p}\n"); t=e
OUT.write_text("\n".join(rows),encoding="utf-8-sig")
print({"path":str(OUT),"cues":len(rows),"start":start,"end":start+dur})
