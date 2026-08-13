from pathlib import Path
import subprocess

FF = Path(r"C:\Users\amd\hermes\node_modules\ffmpeg-static\ffmpeg.exe")
SRC = Path(r"C:\Users\amd\Downloads\Candle_burning_on_wooden_table_202608112303.mp4")
VOICE = Path(r"C:\Users\amd\module\bible_healing\runs\ep01_anxious_night\voice_ab\pastor_calm_10s_M4_low.wav")
OUTDIR = Path(r"C:\Users\amd\module\bible_healing\runs\ep01_anxious_night\pingpong_5min_sample")
CYCLE = OUTDIR / "candle-forward-reverse-8s.mp4"
ASS = OUTDIR / "pingpong-sample.ass"
OUT = OUTDIR / "candle-pingpong-5min-with-voice-subtitles.mp4"

def main():
    OUTDIR.mkdir(parents=True, exist_ok=True)
    subprocess.run([str(FF), "-y", "-hide_banner", "-loglevel", "error", "-i", str(SRC),
                    "-vf", "reverse", "-an", "-c:v", "libx264", "-preset", "ultrafast", "-crf", "23", str(OUTDIR / "reverse.mp4")], check=True)
    rev = OUTDIR / "reverse.mp4"
    subprocess.run([str(FF), "-y", "-hide_banner", "-loglevel", "error", "-i", str(SRC), "-i", str(rev),
                    "-filter_complex", "[0:v][1:v]concat=n=2:v=1:a=0,trim=duration=8,setpts=N/FRAME_RATE/TB[v]",
                    "-map", "[v]", "-an", "-c:v", "libx264", "-preset", "ultrafast", "-crf", "23", str(CYCLE)], check=True)
    header = """[Script Info]\nScriptType: v4.00+\nPlayResX: 1920\nPlayResY: 1080\n\n[V4+ Styles]\nFormat: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding\nStyle: Default,Malgun Gothic,48,&H00FFFFFF,&H00FFFFFF,&H00101010,&H80000000,0,0,0,0,100,100,0,0,1,3,1,2,80,80,80,1\n\n[Events]\nFormat: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text\n"""
    lines = [header]
    text = "오늘 밤, 잠시 모든 걱정을 내려놓으셔도 괜찮습니다."
    for i in range(26):
        start = i * 11.872653
        if start >= 300: break
        h = int(start // 3600); m = int((start % 3600)//60); s = start % 60
        e = min(start + 11.2, 300)
        eh = int(e // 3600); em = int((e % 3600)//60); es = e % 60
        lines.append(f"Dialogue: 0,{h}:{m:02d}:{s:05.2f},{eh}:{em:02d}:{es:05.2f},Default,,0,0,0,,{text}\n")
    ASS.write_text("".join(lines), encoding="utf-8")
    ass = str(ASS).replace("\\", "/").replace(":", "\\:")
    vf = f"subtitles='{ass}'"
    subprocess.run([str(FF), "-y", "-hide_banner", "-loglevel", "error", "-stream_loop", "-1", "-i", str(CYCLE),
                    "-stream_loop", "-1", "-i", str(VOICE), "-t", "300", "-vf", vf,
                    "-map", "0:v:0", "-map", "1:a:0", "-c:v", "libx264", "-preset", "ultrafast", "-crf", "23",
                    "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "128k", "-shortest", str(OUT)], check=True)
    print({"output": str(OUT), "duration_sec": 300, "cycle": str(CYCLE)})

if __name__ == "__main__": main()
