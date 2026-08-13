from pathlib import Path
import subprocess
R=Path(r"C:\Users\amd\module");J=R/"bible_healing/runs/ep01_anxious_night/hermes_jobs/actual_first3min_pause_split";W=J/"trial_persistent_chapter_render";W.mkdir(exist_ok=True);FF=Path(r"C:\Users\amd\hermes\node_modules\ffmpeg-static\ffmpeg.exe");BG=R/"bible_healing/runs/ep01_anxious_night/hermes_jobs/voice_pastor_calm_M4/locked_voice_slow333/background_slow033_3min.mp4";A=J/"trial_longform_caption_render_v2/audio.wav";BASE=J/"trial_longform_caption_render_v2/captions.ass";O=J/"final-first3min-trial-persistent-chapters.mp4"
def run(c):subprocess.run(c,check=True)
chapters=[(0,25,"밤의 불안"),(25,48,"마음의 쉼"),(48,122,"시편 4편"),(122,155,"기도"),(155,180,"회복")]
events=[]
for st,en,label in chapters:
 def tm(v):return f"0:{v//60:02d}:{v%60:05.2f}"
 events.append(f"Dialogue: 2,{tm(st)},{tm(en)},Chapter,,0,0,0,,{label}\n")
ass=W/"captions_persistent_chapters.ass";text=BASE.read_text(encoding='utf-8-sig');needle="Style: Default,Malgun Gothic,72,&H00FFFFFF,&H00FFFFFF,&H00000000,&H80000000,-1,0,0,0,100,100,0,0,1,4,2,2,120,120,70,1";text=text.replace(needle,needle+"\nStyle: Chapter,Malgun Gothic,36,&H00E8E0D0,&H00E8E0D0,&H00000000,&H90000000,0,0,0,0,100,100,0,0,1,2,1,9,120,120,90,1");text=text.replace("Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text\n","Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text\n"+''.join(events));ass.write_text(text,encoding='utf-8-sig');esc=str(ass).replace('\\','/').replace(':','\\:');run([str(FF),'-y','-hide_banner','-loglevel','error','-i',str(BG),'-i',str(A),'-vf',f"subtitles='{esc}'",'-t','180','-map','0:v:0','-map','1:a:0','-c:v','libx264','-preset','ultrafast','-crf','23','-pix_fmt','yuv420p','-c:a','aac','-b:a','128k','-shortest','-movflags','+faststart',str(O)]);print({'output':str(O),'duration':180,'persistent_chapters':True,'max_lines':1,'font_size':36})
