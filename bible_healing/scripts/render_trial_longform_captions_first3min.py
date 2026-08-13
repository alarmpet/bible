from pathlib import Path
import json, subprocess

ROOT=Path(r"C:\Users\amd\module"); JOB=ROOT/"bible_healing/runs/ep01_anxious_night/hermes_jobs/actual_first3min_pause_split"; SRC=JOB/"true_sync_render"; W=JOB/"trial_longform_caption_render"; W.mkdir(exist_ok=True)
FF=Path(r"C:\Users\amd\hermes\node_modules\ffmpeg-static\ffmpeg.exe"); FP=Path(r"C:\Users\amd\hermes\node_modules\@ffprobe-installer\win32-x64\ffprobe.exe"); BG=ROOT/"bible_healing/runs/ep01_anxious_night/hermes_jobs/voice_pastor_calm_M4/locked_voice_slow333/background_slow033_3min.mp4"; OUT=JOB/"final-first3min-trial-longform-captions.mp4"
POL=json.loads((ROOT/"bible_healing/config/final_render_policy.json").read_text(encoding="utf-8")); MAX=18; TOTAL=36
def run(c): subprocess.run(c,check=True)
def dur(p): return float(subprocess.check_output([str(FP),"-v","error","-show_entries","format=duration","-of","default=nw=1:nk=1",str(p)],text=True).strip())
def at(v): return f"{int(v//3600)}:{int(v%3600//60):02d}:{v%60:05.2f}"
def chunks(text):
    words=text.split(); out=[]; cur=[]
    for word in words:
        candidate=" ".join(cur+[word])
        if len(candidate)<=TOTAL: cur.append(word); continue
        if cur: out.append(" ".join(cur))
        cur=[word]
    if cur: out.append(" ".join(cur))
    return out
def two_lines(s):
    if len(s)<=MAX: return s
    words=s.split(); best=None
    for i in range(1,len(words)):
        a=" ".join(words[:i]); b=" ".join(words[i:])
        if len(a)<=MAX and len(b)<=MAX:
            score=abs(len(a)-len(b))
            if best is None or score<best[0]: best=(score,a,b)
    return (best[1]+r"\N"+best[2]) if best else s
sc=json.loads((JOB/"scenes.json").read_text(encoding="utf-8")); aud=[]; ev=[]; t=0.0
for scene in sc:
  for seg in scene.get("segments",[]):
    speaker=seg["speaker"]; sid=seg["seg_id"]; voice="M4" if speaker=="scripture" else "F5"; src=JOB/"segments"/f"{sid}_{speaker}_{voice}.wav"; out=W/f"{sid}_{voice}.wav"
    filt="asetrate=44100*0.92,aresample=44100,atempo=1.0869565,equalizer=f=150:t=q:w=1.0:g=1.5,highpass=f=65,lowpass=f=8500" if speaker=="scripture" else "anull"; run([str(FF),"-y","-hide_banner","-loglevel","error","-i",str(src),"-af",filt,"-c:a","pcm_s16le",str(out)])
    d=dur(out); start=t; end=min(t+d,180); cs=chunks(seg.get("text", "")); weights=[max(1,len(x)) for x in cs]; total=sum(weights) or 1; cursor=start
    for i,c in enumerate(cs):
      ce=end if i==len(cs)-1 else start+d*sum(weights[:i+1])/total; ev.append(f"Dialogue: 0,{at(cursor)},{at(ce)},Default,,0,0,0,,{two_lines(c)}\n"); cursor=ce
    aud.append(out); t=end
    if t>=180: break
  if t>=180: break
alist=W/"audio.txt"; alist.write_text("\n".join(f"file '{p.as_posix()}'" for p in aud),encoding="utf-8"); audio=W/"audio.wav"; run([str(FF),"-y","-hide_banner","-loglevel","error","-f","concat","-safe","0","-i",str(alist),"-t","180","-c:a","pcm_s16le",str(audio)])
ass=W/"captions.ass"; ass.write_text("""[Script Info]\nScriptType: v4.00+\nPlayResX: 1920\nPlayResY: 1080\nScaledBorderAndShadow: yes\nWrapStyle: 0\n\n[V4+ Styles]\nFormat: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding\nStyle: Default,Malgun Gothic,72,&H00FFFFFF,&H00FFFFFF,&H00000000,&H80000000,-1,0,0,0,100,100,0,0,1,4,2,2,120,120,70,1\n\n[Events]\nFormat: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text\n"""+"".join(ev),encoding="utf-8-sig")
esc=str(ass).replace('\\','/').replace(':','\\:'); run([str(FF),"-y","-hide_banner","-loglevel","error","-i",str(BG),"-i",str(audio),"-vf",f"subtitles='{esc}'","-t","180","-map","0:v:0","-map","1:a:0","-c:v","libx264","-preset","ultrafast","-crf","23","-pix_fmt","yuv420p","-c:a","aac","-b:a","128k","-shortest","-movflags","+faststart",str(OUT)])
print({"output":str(OUT),"duration":180,"caption_mode":"balanced_two_line_longform","max_line_chars":MAX,"max_total_chars":TOTAL,"base_preserved":True})
