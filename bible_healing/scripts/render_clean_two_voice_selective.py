from pathlib import Path
import json, subprocess, sys
sys.path.insert(0,str(Path(__file__).resolve().parent))
from render_actual_first3min_locked import run

ROOT=Path(r"C:\Users\amd\module")
JOB=ROOT/"bible_healing/runs/ep01_anxious_night/hermes_jobs/actual_first3min_clean_two_voice"
BG=ROOT/"bible_healing/runs/ep01_anxious_night/hermes_jobs/voice_pastor_calm_M4/locked_voice_slow333/background_slow0333_3min.mp4"
FF=Path(r"C:\Users\amd\hermes\node_modules\ffmpeg-static\ffmpeg.exe")
FP=Path(r"C:\Users\amd\hermes\node_modules\@ffprobe-installer\win32-x64\ffprobe.exe")
OUT=JOB/"final-first3min-clean-two-voice-selective-slow0333.mp4"; W=JOB/"selective_render"; W.mkdir(exist_ok=True)
def dur(p): return float(subprocess.check_output([str(FP),"-v","error","-show_entries","format=duration","-of","default=nw=1:nk=1",str(p)],text=True).strip())
def at(v):
 h=int(v//3600);m=int((v%3600)//60);s=v%60;return f"{h}:{m:02d}:{s:05.2f}"
sc=json.loads((JOB/"scenes.json").read_text(encoding="utf-8")); aud=[]; t=0; body=[]
for i,s in enumerate(sc,1):
 src=JOB/f"scene_{i}.wav"; out=W/f"scene_{i}_processed.wav"; speaker=(s.get("segments") or [{}])[0].get("speaker")
 filt="asetrate=44100*0.92,aresample=44100,atempo=1.0869565,equalizer=f=150:t=q:w=1.0:g=1.5,highpass=f=65,lowpass=f=8500" if speaker=="scripture" else "anull"
 run([str(FF),"-y","-hide_banner","-loglevel","error","-i",str(src),"-af",filt,"-c:a","pcm_s16le",str(out)])
 d=dur(out); e=min(t+d,180); txt=(s.get("narration") or "").replace("\n"," ").strip(); body.append(f"Dialogue: 0,{at(t)},{at(e)},Default,,0,0,0,,{txt}\n"); aud.append(out); t=e
al=W/"audio.txt";al.write_text("\n".join(f"file '{p.as_posix()}'" for p in aud),encoding="utf-8"); audio=W/"audio.wav";run([str(FF),"-y","-hide_banner","-loglevel","error","-f","concat","-safe","0","-i",str(al),"-t","180","-c:a","pcm_s16le",str(audio)])
ass=W/"subtitles.ass";ass.write_text("""[Script Info]\nScriptType: v4.00+\nPlayResX: 1920\nPlayResY: 1080\nScaledBorderAndShadow: yes\n\n[V4+ Styles]\nFormat: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding\nStyle: Default,Malgun Gothic,108,&H00FFFFFF,&H00FFFFFF,&H00000000,&H80000000,-1,0,0,0,100,100,0,0,1,6,3,2,100,100,90,1\n\n[Events]\nFormat: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text\n"""+"".join(body),encoding="utf-8-sig")
esc=str(ass).replace('\\','/').replace(':','\\:');run([str(FF),"-y","-hide_banner","-loglevel","error","-i",str(BG),"-i",str(audio),"-vf",f"subtitles='{esc}'","-t","180","-map","0:v:0","-map","1:a:0","-c:v","libx264","-preset","ultrafast","-crf","23","-pix_fmt","yuv420p","-c:a","aac","-b:a","128k","-shortest","-movflags","+faststart",str(OUT)])
print({"output":str(OUT),"duration":180,"female_pitch":"unchanged","male_pitch":"-8%","captions_font_px":108,"video_speed":0.333})
