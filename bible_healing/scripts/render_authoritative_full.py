from pathlib import Path
import subprocess
R=Path(r"C:\Users\amd\module"); J=R/"bible_healing/runs/ep01_anxious_night/hermes_jobs/full"; D=Path(r"D:\bible_healing_ep01"); FF=Path(r"C:\Users\amd\hermes\node_modules\ffmpeg-static\ffmpeg.exe"); FP=Path(r"C:\Users\amd\hermes\node_modules\@ffprobe-installer\win32-x64\ffprobe.exe")
BG=R/"bible_healing/assets/movie-sample/pingpong-1min"; A=J/"authoritative_audio_rebuild/full-authoritative-audio.wav"; ASS=J/"subtitles-full-audio-aligned.ass"; OUT=D/"final/deploy-ep01-authoritative-audio-aligned.mp4"; W=D/"work/authoritative_audio_rebuild"; W.mkdir(parents=True,exist_ok=True); OUT.parent.mkdir(parents=True,exist_ok=True)
dur=float(subprocess.check_output([str(FP),'-v','error','-show_entries','format=duration','-of','default=nw=1:nk=1',str(A)],text=True).strip())
samples=sorted(BG.glob('*.mp4')); lst=W/'background_concat.txt'; lst.write_text('\n'.join(f"file '{p.as_posix()}'" for _ in range(6) for p in samples),encoding='utf-8')
e=str(ASS).replace('\\','/').replace(':','\\:'); vf=f"setpts=3*PTS,trim=duration={dur:.3f},subtitles='{e}'"
subprocess.run([str(FF),'-y','-hide_banner','-loglevel','error','-f','concat','-safe','0','-i',str(lst),'-i',str(A),'-vf',vf,'-t',str(dur),'-map','0:v:0','-map','1:a:0','-c:v','libx264','-preset','ultrafast','-crf','30','-pix_fmt','yuv420p','-c:a','aac','-b:a','192k','-movflags','+faststart',str(OUT)],check=True)
print({'output':str(OUT),'duration':dur,'samples':len(samples),'audio_source':str(A)})
