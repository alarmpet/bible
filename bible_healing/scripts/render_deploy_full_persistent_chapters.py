from pathlib import Path
import json, subprocess
R=Path(r"C:\Users\amd\module")
J=R/"bible_healing/runs/ep01_anxious_night/hermes_jobs/full"
FF=Path(r"C:\Users\amd\hermes\node_modules\ffmpeg-static\ffmpeg.exe")
FP=Path(r"C:\Users\amd\hermes\node_modules\@ffprobe-installer\win32-x64\ffprobe.exe")
SRC=J/"final-ep01-full.mp4"; OUT=J/"deploy-ep01-full-persistent-chapters.mp4"; W=J/"deploy_persistent_chapters"; W.mkdir(exist_ok=True)
def run(c): subprocess.run(c,check=True)
def fmt(t): return f"{int(t//3600)}:{int(t%3600//60):02d}:{t%60:05.2f}"
dur=float(subprocess.check_output([str(FP),"-v","error","-show_entries","format=duration","-of","default=nw=1:nk=1",str(SRC)],text=True).strip())
titles=[(0,"밤의 불안"),(300,"마음의 쉼"),(600,"시편의 기도"),(900,"두려움 내려놓기"),(1200,"하나님의 위로"),(1500,"기다림과 믿음"),(1800,"마음의 회복"),(2100,"감사와 평안"),(2400,"오늘의 기도"),(2700,"마무리"),(3000,"평안")]
titles=[x for x in titles if x[0]<dur]; events=[]
for i,(st,label) in enumerate(titles): events.append(f"Dialogue: 2,{fmt(st)},{fmt(titles[i+1][0] if i+1<len(titles) else dur)},Chapter,,0,0,0,,{label}\n")
ass=W/"deploy_chapters.ass"; ass.write_text("""[Script Info]\nScriptType: v4.00+\nPlayResX: 1920\nPlayResY: 1080\nWrapStyle: 0\n\n[V4+ Styles]\nFormat: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding\nStyle: Chapter,Malgun Gothic,36,&H00E8E0D0,&H00E8E0D0,&H00000000,&H90000000,0,0,0,0,100,100,0,0,1,2,1,9,120,120,90,1\n\n[Events]\nFormat: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text\n"""+''.join(events),encoding='utf-8-sig')
esc=str(ass).replace('\\','/').replace(':','\\:')
run([str(FF),'-y','-hide_banner','-loglevel','error','-i',str(SRC),'-vf',f"subtitles='{esc}'",'-c:v','libx264','-preset','ultrafast','-crf','23','-pix_fmt','yuv420p','-c:a','copy','-movflags','+faststart',str(OUT)])
print({'output':str(OUT),'duration':dur,'chapters':len(events),'persistent':True,'font_size':36})
