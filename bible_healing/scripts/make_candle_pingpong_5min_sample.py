from pathlib import Path
import subprocess

FF = Path(r"C:\Users\amd\hermes\node_modules\ffmpeg-static\ffmpeg.exe")
SRC = Path(r"C:\Users\amd\Downloads\Candle_burning_on_wooden_table_202608112303.mp4")
VOICE = Path(r"C:\Users\amd\module\bible_healing\runs\ep01_anxious_night\voice_ab\pastor_calm_10s_M4_low.wav")
OUTDIR = Path(r"C:\Users\amd\module\bible_healing\runs\ep01_anxious_night\pingpong_5min_sample")
OUT = OUTDIR / "candle-pingpong-5min-with-voice-subtitles.mp4"
ASS = OUTDIR / "pingpong-sample.ass"

def ts(sec: float) -> str:
    h = int(sec // 3600); m = int((sec % 3600) // 60); s = sec % 60
    return f"{h}:{m:02d}:{int(s):02d}.{int((s-int(s))*100):02d}"

def main() -> None:
    OUTDIR.mkdir(parents=True, exist_ok=True)
    # One forward + reverse cycle is 8 seconds.  The final repeated frame is
    # trimmed by the concat filter, so the turn does not visibly jump.
    header = """[Script Info]\nScriptType: v4.00+\nPlayResX: 1920\nPlayResY: 1080\n\n[V4+ Styles]\nFormat: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding\nStyle: Default,Malgun Gothic,48,&H00FFFFFF,&H00FFFFFF,&H00101010,&H80000000,0,0,0,0,100,100,0,0,1,3,1,2,80,80,80,1\n\n[Events]\nFormat: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text\n"""
    lines = [header]
    text = "오늘 밤, 잠시 모든 걱정을 내려놓으셔도 괜찮습니다."
    # The 11.87-second reference voice is looped as a clear technical sample.
    # Repeat its subtitle cue at the same cadence for sync inspection.
    for i in range(26):
        start = i * 11.872653
        end = min(start + 11.2, 300.0)
        if start >= 300: break
        lines.append(f"Dialogue: 0,{ts(start)},{ts(end)},Default,,0,0,0,,{text}\n")
    ASS.write_text("".join(lines), encoding="utf-8")
    ass = str(ASS).replace("\\", "/").replace(":", "\\:")
    # Video is looped as forward/reverse pairs. Audio is the approved low M4
    # sample looped independently and then trimmed to exactly five minutes.
    vf = f"subtitles='{ass}'"
    cmd = [str(FF), "-y", "-hide_banner", "-loglevel", "error",
           "-stream_loop", "-1", "-i", str(SRC), "-stream_loop", "-1", "-i", str(VOICE),
           "-filter_complex", "[0:v]split[a][b];[b]reverse[br];[a][br]concat=n=2:v=1:a=0,trim=duration=8,setpts=N/FRAME_RATE/TB[v0];[v0]loop=loop=-1:size=192: start=0,trim=duration=300,setpts=N/FRAME_RATE/TB," + vf + "[v]",
           "-map", "[v]", "-map", "1:a:0", "-t", "300", "-af", "aresample=48000",
           "-c:v", "libx264", "-preset", "fast", "-crf", "20", "-pix_fmt", "yuv420p",
           "-c:a", "aac", "-b:a", "192k", "-shortest", "-movflags", "+faststart", str(OUT)]
    subprocess.run(cmd, check=True)
    print({"output": str(OUT), "duration_sec": 300, "pattern": "1,2,3,4,4,3,2,1"})

if __name__ == "__main__":
    main()
