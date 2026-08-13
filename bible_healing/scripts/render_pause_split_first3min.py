from pathlib import Path
import json,subprocess

ROOT=Path(r"C:\Users\amd\module"); JOB=ROOT/"bible_healing/runs/ep01_anxious_night/hermes_jobs/actual_first3min_pause_split"; BG=ROOT/"bible_healing/runs/ep01_anxious_night/hermes_jobs/voice_pastor_calm_M4/locked_voice_slow333/background_slow033_3min.mp4"; FF=Path(r"C:\Users\amd\hermes\node_modules\ffmpeg-static\ffmpeg.exe"); FP=Path(r"C:\Users\amd\hermes\node_modules\@ffprobe-installer\win32-x64\ffprobe.exe"); W=JOB/"render"; W.mkdir(exist_ok=True); OUT=JOB/"final-first3min-pause-split-2line-slow0333.mp4"
def run(c): subprocess.run(c,check=True)
def dur(p): return float(subprocess.check_output([str(FP),"-v","error","-show_entries","format=duration","-of","default=nw=1:nk=1",str(p)],text=True).strip())
def at(v):
 h=int(v//3600);m=int((v%3600)//60);s=v%60;return f"{h}:{m:02d}:{s:05.2f}"
sc=json.loads((JOB/"scenes.json").read_text(encoding="utf-8")); aud=[]; events=[]; t=0
for i,s in enumerate(sc,1):
 src=JOB/f"scene_{i}.wav"; out=W/f"scene_{i}_processed.wav"; speaker=(s.get("segments") or [{}])[0].get("speaker"); filt="asetrate=44100*0.92,aresample=44100,atempo=1.0869565,equalizer=f=150:t=q:w=1.0:g=1.5,highpass=f=65,lowpass=f=8500" if speaker=="scripture" else "anull"; run([str(FF),"-y","-hide_banner","-loglevel","error","-i",str(src),"-af",filt,"-c:a","pcm_s16le",str(out)]); d=dur(out); e=min(t+d,180); aud.append(out)
 for seg in s.get("segments",[]):
  text=(seg.get("text") or "").strip();
  if not text: continue
  # Split captions to two lines without shrinking the font.
  words=text.split(); lines=[]; cur=""
  for w in words:
   if len(cur)+len(w)+(1 if cur else 0)<=20: cur=(cur+" "+w).strip()
   else: lines.append(cur); cur=w
  if cur: lines.append(cur)
  # Use one event per scene segment; ASS wraps at two lines only.
  caption=r"\N".join(lines[:2])
  events.append(f"Dialogue: 0,{at(t)},{at(e)},Default,,0,0,0,,{caption}\n")
 t=e
al=W/"audio.txt";al.write_text("\n".join(f"file '{p.as_posix()}'" for p in aud),encoding="utf-8"); audio=W/"audio.wav";run([str(FF),"-y","-hide_banner","-loglevel","error","-f","concat","-safe","0","-i",str(al),"-t","180","-c:a","pcm_s16le",str(audio)])
ass=W/"captions_108px.ass";ass.write_text("""[Script Info]\nScriptType: v4.00+\nPlayResX: 1920\nPlayResY: 1080\nScaledBorderAndShadow: yes\nWrapStyle: 0\n\n[V4+ Styles]\nFormat: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding\nStyle: Default,Malgun Gothic,108,&H00FFFFFF,&H00FFFFFF,&H00000000,&H80000000,-1,0,0,0,100,100,0,0,1,6,3,2,100,100,90,1\n\n[Events]\nFormat: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text\n"""+"".join(events),encoding="utf-8-sig")
esc=str(ass).replace('\\','/').replace(':','\\:');run([str(FF),"-y","-hide_banner","-loglevel","error","-i",str(BG),"-i",str(audio),"-vf",f"subtitles='{esc}'","-t","180","-map","0:v:0","-map","1:a:0","-c:v","libx264","-preset","ultrafast","-crf","23","-pix_fmt","yuv420p","-c:a","aac","-b:a","128k","-shortest","-movflags","+faststart",str(OUT)])
print({"output":str(OUT),"duration":180,"captions":"108px_two_line","male_pitch":"-8%","video_speed":0.333})
