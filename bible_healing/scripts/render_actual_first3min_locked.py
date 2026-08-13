from pathlib import Path
import subprocess, json

FF=Path(r"C:\Users\amd\hermes\node_modules\ffmpeg-static\ffmpeg.exe")
ROOT=Path(r"C:\Users\amd\module")
JOB=ROOT/"bible_healing/runs/ep01_anxious_night/hermes_jobs/actual_first3min_locked_M4"
BG=ROOT/"bible_healing/runs/ep01_anxious_night/hermes_jobs/voice_pastor_calm_M4/locked_voice_slow333"
OUT=JOB/"final-actual-first3min-M4-low-pitch-slow0333.mp4"
WORK=JOB/"render_work"; WORK.mkdir(exist_ok=True)
def run(c): subprocess.run(c,check=True)
def main():
    processed=[]
    for i in range(1,13):
        src=JOB/f"scene_{i}.wav"; dst=WORK/f"scene_{i}_low.wav"; processed.append(dst)
        run([str(FF),"-y","-hide_banner","-loglevel","error","-i",str(src),"-af","asetrate=44100*0.92,aresample=44100,atempo=1.0869565,equalizer=f=150:t=q:w=1.0:g=1.5,highpass=f=65,lowpass=f=8500","-c:a","pcm_s16le",str(dst)])
    al=WORK/"audio.txt"; al.write_text("\n".join(f"file '{x.as_posix()}'" for x in processed),encoding="utf-8")
    audio=WORK/"actual_audio_first3min.wav"
    run([str(FF),"-y","-hide_banner","-loglevel","error","-f","concat","-safe","0","-i",str(al),"-t","180","-c:a","pcm_s16le",str(audio)])
    # Build cues from actual scene durations, keeping the scene text mapping.
    scenes=json.loads((JOB/"scenes.json").read_text(encoding="utf-8"))
    fp=Path(r"C:\Users\amd\hermes\node_modules\@ffprobe-installer\win32-x64\ffprobe.exe")
    t=0.0; body=[]
    for i,s in enumerate(scenes):
        if t>=180: break
        wav=processed[i]; d=float(subprocess.check_output([str(fp),"-v","error","-show_entries","format=duration","-of","default=nw=1:nk=1",str(wav)],text=True).strip())
        e=min(t+d,180); text=s.get("narration","").replace("\\N"," ").replace("\n"," ")
        h=int(t//3600);m=int((t%3600)//60);sec=t%60; eh=int(e//3600);em=int((e%3600)//60);es=e%60
        body.append(f"Dialogue: 0,{h}:{m:02d}:{sec:05.2f},{eh}:{em:02d}:{es:05.2f},Default,,0,0,0,,{text}\n")
        t += d
    ass=WORK/"actual_first3min.ass"
    header="""[Script Info]\nScriptType: v4.00+\nPlayResX: 1920\nPlayResY: 1080\n\n[V4+ Styles]\nFormat: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding\nStyle: Default,Malgun Gothic,42,&H00FFFFFF,&H00FFFFFF,&H00101010,&H80000000,0,0,0,0,100,100,0,0,1,3,1,2,80,80,80,1\n\n[Events]\nFormat: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text\n"""
    ass.write_text(header+"".join(body),encoding="utf-8")
    esc=str(ass).replace('\\','/').replace(':','\\:')
    bg=BG/"background_slow033_3min.mp4"
    run([str(FF),"-y","-hide_banner","-loglevel","error","-i",str(bg),"-i",str(audio),"-vf",f"subtitles='{esc}'","-t","180","-map","0:v:0","-map","1:a:0","-c:v","libx264","-preset","ultrafast","-crf","23","-pix_fmt","yuv420p","-c:a","aac","-b:a","128k","-shortest","-movflags","+faststart",str(OUT)])
    print({"output":str(OUT),"duration":180,"voice":"M4_locked_pitch_minus8","speed":0.72,"video_speed":0.333})
if __name__=="__main__": main()
