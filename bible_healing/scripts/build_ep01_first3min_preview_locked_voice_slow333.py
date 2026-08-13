from pathlib import Path
import subprocess

FF=Path(r"C:\Users\amd\hermes\node_modules\ffmpeg-static\ffmpeg.exe")
ROOT=Path(r"C:\Users\amd\module")
BG=ROOT/"bible_healing/assets/movie-sample/pingpong-1min"
VOICE=ROOT/"bible_healing/runs/ep01_anxious_night/voice_ab/pastor_calm_10s_M4_low.wav"
OUTDIR=ROOT/"bible_healing/runs/ep01_anxious_night/hermes_jobs/voice_pastor_calm_M4/locked_voice_slow333"
OUT=OUTDIR/"final-ep01-first-3min-locked-voice-slow333.mp4"

def run(c): subprocess.run(c,check=True)
def at(v):
    h=int(v//3600); m=int((v%3600)//60); s=v%60
    return f"{h}:{m:02d}:{s:05.2f}"

def main():
    OUTDIR.mkdir(parents=True,exist_ok=True)
    vids=sorted(BG.glob("*_pingpong_1min.mp4"))[:3]
    slow=[]
    for i,v in enumerate(vids,1):
        p=OUTDIR/f"bg_{i}_slow033.mp4"; slow.append(p)
        # 3.003x PTS => approximately 0.333x playback speed.
        run([str(FF),"-y","-hide_banner","-loglevel","error","-stream_loop","-1","-i",str(v),"-vf","setpts=3.003*PTS","-t","60","-an","-c:v","libx264","-preset","ultrafast","-crf","23","-pix_fmt","yuv420p",str(p)])
    vl=OUTDIR/"videos.txt"; vl.write_text("\n".join(f"file '{p.as_posix()}'" for p in slow),encoding="utf-8")
    bg3=OUTDIR/"background_slow033_3min.mp4"
    run([str(FF),"-y","-hide_banner","-loglevel","error","-f","concat","-safe","0","-i",str(vl),"-t","180","-an","-c","copy",str(bg3)])
    audio=OUTDIR/"LOCKED_voice_only_loop_180s.wav"
    run([str(FF),"-y","-hide_banner","-loglevel","error","-stream_loop","-1","-i",str(VOICE),"-t","180","-c:a","pcm_s16le",str(audio)])
    ass=OUTDIR/"locked_voice_subtitles.ass"
    header="""[Script Info]\nScriptType: v4.00+\nPlayResX: 1920\nPlayResY: 1080\n\n[V4+ Styles]\nFormat: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding\nStyle: Default,Malgun Gothic,48,&H00FFFFFF,&H00FFFFFF,&H00101010,&H80000000,0,0,0,0,100,100,0,0,1,3,1,2,80,80,80,1\n\n[Events]\nFormat: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text\n"""
    body=[]; text="오늘 밤, 잠시 모든 걱정을 내려놓으셔도 괜찮습니다."
    for i in range(26):
        s=i*11.872653; e=min(s+11.2,180)
        if s>=180: break
        body.append(f"Dialogue: 0,{at(s)},{at(e)},Default,,0,0,0,,{text}\n")
    ass.write_text(header+"".join(body),encoding="utf-8")
    esc=str(ass).replace('\\','/').replace(':','\\:')
    run([str(FF),"-y","-hide_banner","-loglevel","error","-i",str(bg3),"-i",str(audio),"-vf",f"subtitles='{esc}'","-t","180","-map","0:v:0","-map","1:a:0","-c:v","libx264","-preset","ultrafast","-crf","23","-pix_fmt","yuv420p","-c:a","aac","-b:a","128k","-shortest","-movflags","+faststart",str(OUT)])
    print({"output":str(OUT),"duration":180,"locked_voice":str(VOICE),"video_speed_factor":0.333})

if __name__=="__main__": main()
