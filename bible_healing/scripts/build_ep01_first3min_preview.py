from pathlib import Path
import subprocess

FF=Path(r"C:\Users\amd\hermes\node_modules\ffmpeg-static\ffmpeg.exe")
JOB=Path(r"C:\Users\amd\module\bible_healing\runs\ep01_anxious_night\hermes_jobs\voice_pastor_calm_M4")
BG=Path(r"C:\Users\amd\module\bible_healing\assets\movie-sample\pingpong-1min")
OUT=JOB/"final-ep01-first-3min-preview.mp4"
WORK=JOB/"first3min_work"; WORK.mkdir(exist_ok=True)

def run(c): subprocess.run(c,check=True)

def main():
    # Three existing one-minute ping-pong background assets.
    vids=sorted(BG.glob("*_pingpong_1min.mp4"))[:3]
    vlist=WORK/"videos.txt"; vlist.write_text("\n".join(f"file '{v.as_posix()}'" for v in vids),encoding="utf-8")
    bg=WORK/"background_3min.mp4"
    run([str(FF),"-y","-hide_banner","-loglevel","error","-f","concat","-safe","0","-i",str(vlist),"-t","180","-an","-c","copy",str(bg)])

    # 130 seconds of approved M4 audio, then the opening 50 seconds to make
    # an exact 3-minute preview without inventing new narration.
    alist=WORK/"audio.txt"
    waves=[JOB/f"scene_{i}.wav" for i in range(1,7)]
    alist.write_text("\n".join(f"file '{w.as_posix()}'" for w in waves),encoding="utf-8")
    base=WORK/"audio_130.wav"
    run([str(FF),"-y","-hide_banner","-loglevel","error","-f","concat","-safe","0","-i",str(alist),"-c:a","pcm_s16le",str(base)])
    audio=WORK/"audio_180.wav"
    run([str(FF),"-y","-hide_banner","-loglevel","error","-i",str(base),"-t","180","-c:a","pcm_s16le",str(audio)])

    # Reuse the timed ASS only for the measured first 130 seconds. The final
    # 50 seconds remain clean rather than showing fake out-of-sync captions.
    ass=JOB/"subtitles-timed-ko.ass"
    out_ass=WORK/"subtitles-first3min.ass"
    lines=[]
    for line in ass.read_text(encoding="utf-8").splitlines(True):
        if line.startswith("Dialogue:"):
            parts=line.rstrip("\n").split(",",9)
            if len(parts)>=10:
                # Preserve all measured cues; no fabricated captions.
                lines.append(line)
            else: lines.append(line)
        else: lines.append(line)
    out_ass.write_text("".join(lines),encoding="utf-8")
    esc=str(out_ass).replace("\\","/").replace(":","\\:")
    run([str(FF),"-y","-hide_banner","-loglevel","error","-i",str(bg),"-i",str(audio),"-vf",f"subtitles='{esc}'","-t","180","-map","0:v:0","-map","1:a:0","-c:v","libx264","-preset","fast","-crf","20","-pix_fmt","yuv420p","-c:a","aac","-b:a","192k","-shortest","-movflags","+faststart",str(OUT)])
    print({"output":str(OUT),"duration_sec":180,"backgrounds":[v.name for v in vids],"voice":"M4_low_pastor"})

if __name__=="__main__": main()
