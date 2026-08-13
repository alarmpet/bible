from pathlib import Path
import json
R=Path(r"C:\Users\amd\module"); J=R/"bible_healing/runs/ep01_anxious_night/hermes_jobs/full"; M=json.loads((J/"scene_audio_manifest.json").read_text(encoding='utf-8-sig'))
sc={int(x['order']):x for x in json.loads((J/"scenes.json").read_text(encoding='utf-8'))}
# The deployed source is the older 136-scene, ~50-minute audio/video package.
# The locked 110-scene manifest silently truncates captions at 41:36. Recover
# the complete timing from the preserved prelock audio manifest and text from
# script_segments.json when its duration disagrees with the source media.
src=R/"bible_healing/runs/ep01_anxious_night/upload_package/final-ep01-full.mp4"
import subprocess
import re
FP=Path(r"C:\Users\amd\hermes\node_modules\@ffprobe-installer\win32-x64\ffprobe.exe")
probe=json.loads(subprocess.check_output([str(FP),'-v','error','-show_entries','format=duration','-of','json',str(src)],text=True))
media_duration=float(probe['format']['duration'])
if media_duration > float(M.get('durationSeconds',0))+30:
 P=json.loads((J/"scene_audio_manifest.prelock.20260810T094946Z.json").read_text(encoding='utf-8'))['items']
 segs=json.loads((R/"bible_healing/runs/ep01_anxious_night/script_segments.json").read_text(encoding='utf-8-sig'))
 base=M['scenes']
 M['scenes']=[]; cursor=0.0
 for i,item in enumerate(P):
  scene_mp4=J/f"scene_{i+1}_synced.mp4"
  dur=float(subprocess.check_output([str(FP),'-v','error','-select_streams','a:0','-show_entries','stream=duration','-of','default=nw=1:nk=1',str(scene_mp4)],text=True).strip())
  text=segs[i].get('text','') if i < len(segs) else ''
  M['scenes'].append({'order':i+1,'text':text,'duration':dur,'startSeconds':cursor,'endSeconds':cursor+dur})
  cursor += dur
 M['durationSeconds']=cursor
def tm(v): return f"{int(v//3600)}:{int(v%3600//60):02d}:{v%60:05.2f}"
def chunks(s,n=20):
 s=re.sub(r"\s+", " ", re.sub(r"\([^()]*\)|（[^（）]*）", " ", s or "")).strip(); out=[]
 for sentence in re.split(r'(?<=[.!?。！？])\s*',s):
  words=sentence.strip().split(); cur=''
  for word in words:
   q=(cur+' '+word).strip()
   if len(q)<=n: cur=q
   else:
    if cur: out.append(cur)
    cur=word
  if cur: out.append(cur)
 return out
events=[]
for item in M['scenes']:
 o=int(item['order']); s=sc.get(o,{}); text=s.get('narration') or item.get('text') or ''; start=float(item['startSeconds']); end=float(item['endSeconds']); cs=chunks(text); weights=[max(1,len(x)) for x in cs]; total=sum(weights) or 1; cur=start
 for i,c in enumerate(cs):
  ce=end if i==len(cs)-1 else start+(end-start)*sum(weights[:i+1])/total; style='Scripture' if any(x.get('speaker')=='scripture' for x in s.get('segments',[])) else 'Narrator'; events.append(f"Dialogue: 0,{tm(cur)},{tm(ce)},{style},,0,0,0,,{c}\n"); cur=ce
header="""[Script Info]\nScriptType: v4.00+\nPlayResX: 1920\nPlayResY: 1080\nWrapStyle: 0\n\n[V4+ Styles]\nFormat: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding\nStyle: Narrator,Malgun Gothic,72,&H00FFFFFF,&H00FFFFFF,&H00000000,&H80000000,-1,0,0,0,100,100,0,0,1,4,2,2,120,120,70,1\nStyle: Scripture,Malgun Gothic,72,&H00F5F5FF,&H00F5F5FF,&H00000000,&H80000000,-1,0,0,0,100,100,0,0,1,4,2,2,120,120,70,1\nStyle: Chapter,Malgun Gothic,36,&H00E8E0D0,&H00E8E0D0,&H00000000,&H90000000,0,0,0,0,100,100,0,0,1,2,1,9,120,120,90,1\n\n[Events]\nFormat: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text\n"""
out=J/"subtitles-full-audio-aligned.ass"; out.write_text(header+''.join(events),encoding='utf-8-sig'); print({'output':str(out),'events':len(events),'last_end':M['scenes'][-1]['endSeconds']})
