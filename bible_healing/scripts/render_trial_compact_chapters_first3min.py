from pathlib import Path
import subprocess

R=Path(r"C:\Users\amd\module")
J=R/"bible_healing/runs/ep01_anxious_night/hermes_jobs/actual_first3min_pause_split"
W=J/"trial_compact_chapter_render"; W.mkdir(exist_ok=True)
FF=Path(r"C:\Users\amd\hermes\node_modules\ffmpeg-static\ffmpeg.exe")
BG=R/"bible_healing/runs/ep01_anxious_night/hermes_jobs/voice_pastor_calm_M4/locked_voice_slow333/background_slow033_3min.mp4"
BASE=J/"trial_longform_caption_render_v2/captions.ass"
AUDIO=J/"trial_longform_caption_render_v2/audio.wav"
OUT=J/"final-first3min-trial-compact-chapters.mp4"
def run(c): subprocess.run(c,check=True)

chapters=[
    (0,"밤의 불안"),
    (25,"마음의 쉼"),
    (48,"시편 4편"),
    (122,"기도"),
    (155,"회복"),
]
chapter_events=[]
for start,label in chapters:
    # ASS alpha: mostly transparent black box; one-line, smaller than captions.
    h=start//3600; m=(start%3600)//60; s=start%60
    ss=f"{h}:{m:02d}:{s:05.2f}"
    end=start+3
    h=end//3600; m=(end%3600)//60; s=end%60
    ee=f"{h}:{m:02d}:{s:05.2f}"
    chapter_events.append(f"Dialogue: 2,{ss},{ee},Chapter,,0,0,0,,{label}\n")

ass=W/"captions_with_compact_chapters.ass"
base=BASE.read_text(encoding="utf-8-sig")
base=base.replace("Style: Default,Malgun Gothic,72,&H00FFFFFF,&H00FFFFFF,&H00000000,&H80000000,-1,0,0,0,100,100,0,0,1,4,2,2,120,120,70,1", "Style: Default,Malgun Gothic,72,&H00FFFFFF,&H00FFFFFF,&H00000000,&H80000000,-1,0,0,0,100,100,0,0,1,4,2,2,120,120,70,1\nStyle: Chapter,Malgun Gothic,36,&H00E8E0D0,&H00E8E0D0,&H00000000,&H90000000,0,0,0,0,100,100,0,0,1,2,1,9,120,120,90,1")
base=base.replace("Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text\n", "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text\n"+"".join(chapter_events))
ass.write_text(base,encoding="utf-8-sig")
esc=str(ass).replace('\\','/').replace(':','\\:')
run([str(FF),"-y","-hide_banner","-loglevel","error","-i",str(BG),"-i",str(AUDIO),"-vf",f"subtitles='{esc}'","-t","180","-map","0:v:0","-map","1:a:0","-c:v","libx264","-preset","ultrafast","-crf","23","-pix_fmt","yuv420p","-c:a","aac","-b:a","128k","-shortest","-movflags","+faststart",str(OUT)])
print({"output":str(OUT),"duration":180,"chapter_overlay":"compact_one_line_36px_3sec","base_preserved":True})
