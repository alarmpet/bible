from pathlib import Path
import subprocess
R=Path(r"C:\Users\amd\module"); J=R/"bible_healing/runs/ep01_anxious_night/hermes_jobs/full"; FF=Path(r"C:\Users\amd\hermes\node_modules\ffmpeg-static\ffmpeg.exe")
W=J/"authoritative_audio_rebuild"; W.mkdir(exist_ok=True)
items=sorted(J.glob("scene_*.wav"),key=lambda p:int(p.stem.split('_')[1]))
if len(items)!=110: raise SystemExit(f"expected 110 freshly generated scene WAVs, found {len(items)}")
lst=W/"scene_audio_concat.txt"; lst.write_text("\n".join(f"file '{p.as_posix()}'" for p in items),encoding='utf-8')
out=W/"full-authoritative-audio.wav"
subprocess.run([str(FF),'-y','-hide_banner','-loglevel','error','-f','concat','-safe','0','-i',str(lst),'-vn','-ac','2','-ar','48000','-c:a','pcm_s16le',str(out)],check=True)
print({'output':str(out),'scenes':len(items)})
