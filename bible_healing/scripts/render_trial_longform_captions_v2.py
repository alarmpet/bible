from pathlib import Path
import json,subprocess
R=Path(r"C:\Users\amd\module");J=R/"bible_healing/runs/ep01_anxious_night/hermes_jobs/actual_first3min_pause_split";W=J/"trial_longform_caption_render_v2";W.mkdir(exist_ok=True);FF=Path(r"C:\Users\amd\hermes\node_modules\ffmpeg-static\ffmpeg.exe");FP=Path(r"C:\Users\amd\hermes\node_modules\@ffprobe-installer\win32-x64\ffprobe.exe");BG=R/"bible_healing/runs/ep01_anxious_night/hermes_jobs/voice_pastor_calm_M4/locked_voice_slow333/background_slow033_3min.mp4";O=J/"final-first3min-trial-longform-captions-v2.mp4";M=20;T=40
def run(c):subprocess.run(c,check=True)
def d(p):return float(subprocess.check_output([str(FP),'-v','error','-show_entries','format=duration','-of','default=nw=1:nk=1',str(p)],text=True))
def a(v):return f"{int(v//3600)}:{int(v%3600//60):02d}:{v%60:05.2f}"
def split(s):
 w=s.split();o=[];c=[]
 for x in w:
  if len(' '.join(c+[x]))<=T:c.append(x)
  else:o.append(' '.join(c));c=[x]
 if c:o.append(' '.join(c))
 return o
def fmt(s):
 if len(s)<=M:return s
 w=s.split();c=[]
 for i in range(1,len(w)):
  x=' '.join(w[:i]);y=' '.join(w[i:])
  if len(x)<=M and len(y)<=M:c.append((abs(len(x)-len(y)),x,y))
 if c:
  _,x,y=min(c);return x+r'\N'+y
 return s[:M]+r'\N'+s[M:M*2]
sc=json.loads((J/'scenes.json').read_text(encoding='utf-8'));A=[];E=[];t=0
for S in sc:
 for q in S.get('segments',[]):
  sp=q['speaker'];sid=q['seg_id'];vo='M4' if sp=='scripture' else 'F5';src=J/'segments'/f'{sid}_{sp}_{vo}.wav';out=W/f'{sid}_{vo}.wav';f='asetrate=44100*0.92,aresample=44100,atempo=1.0869565,equalizer=f=150:t=q:w=1.0:g=1.5,highpass=f=65,lowpass=f=8500' if sp=='scripture' else 'anull';run([str(FF),'-y','-hide_banner','-loglevel','error','-i',str(src),'-af',f,'-c:a','pcm_s16le',str(out)]);z=d(out);st=t;en=min(t+z,180);cs=split(q.get('text',''));ws=[max(1,len(x)) for x in cs];tot=sum(ws) or 1;cur=st
  for i,x in enumerate(cs):ce=en if i==len(cs)-1 else st+z*sum(ws[:i+1])/tot;E.append(f'Dialogue: 0,{a(cur)},{a(ce)},Default,,0,0,0,,{fmt(x)}\n');cur=ce
  A.append(out);t=en
  if t>=180:break
 if t>=180:break
l=W/'audio.txt';l.write_text('\n'.join(f"file '{x.as_posix()}'" for x in A),encoding='utf-8');au=W/'audio.wav';run([str(FF),'-y','-hide_banner','-loglevel','error','-f','concat','-safe','0','-i',str(l),'-t','180','-c:a','pcm_s16le',str(au)])
ass=W/'captions.ass';ass.write_text("""[Script Info]\nScriptType: v4.00+\nPlayResX: 1920\nPlayResY: 1080\nWrapStyle: 0\n\n[V4+ Styles]\nFormat: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding\nStyle: Default,Malgun Gothic,72,&H00FFFFFF,&H00FFFFFF,&H00000000,&H80000000,-1,0,0,0,100,100,0,0,1,4,2,2,120,120,70,1\n\n[Events]\nFormat: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text\n"""+''.join(E),encoding='utf-8-sig');esc=str(ass).replace('\\','/').replace(':','\\:');run([str(FF),'-y','-hide_banner','-loglevel','error','-i',str(BG),'-i',str(au),'-vf',f"subtitles='{esc}'",'-t','180','-map','0:v:0','-map','1:a:0','-c:v','libx264','-preset','ultrafast','-crf','23','-pix_fmt','yuv420p','-c:a','aac','-b:a','128k','-shortest','-movflags','+faststart',str(O)]);print({'output':str(O),'duration':180,'max_line':M,'max_lines':2,'base_preserved':True})
