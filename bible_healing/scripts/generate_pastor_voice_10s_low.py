from pathlib import Path
import subprocess
import sys

ROOT = Path(r"C:\Users\amd\supertonic3-local-tts-20260517-r4\supertonic3-local-tts")
RAW = Path(r"C:\Users\amd\module\bible_healing\runs\ep01_anxious_night\voice_ab\pastor_calm_10s_M4_raw.wav")
OUT = Path(r"C:\Users\amd\module\bible_healing\runs\ep01_anxious_night\voice_ab\pastor_calm_10s_M4_low.wav")
FFMPEG = Path(r"C:\Users\amd\hermes\node_modules\ffmpeg-static\ffmpeg.exe")
sys.path.insert(0, str(ROOT / "src"))
from supertonic3_engine import Supertonic3Engine

text = "오늘 밤, 잠시 모든 걱정을 내려놓으셔도 괜찮습니다. 하나님께서 지금 이 순간에도 당신 곁에 계십니다."
engine = Supertonic3Engine(output_dir=OUT.parent)
engine.synthesize_to_file(
    text=text, output_path=RAW, voice="M4", lang="ko", speed=0.72,
    total_step=24, silence_duration=0.65, verbose=False,
)

# Lower pitch while preserving the speaking duration, then gently warm the
# low-mid range without making the voice boomy or muddy.
subprocess.run([
    str(FFMPEG), "-y", "-hide_banner", "-loglevel", "error", "-i", str(RAW),
    "-af", "asetrate=44100*0.92,aresample=44100,atempo=1.0869565,"
           "equalizer=f=150:t=q:w=1.0:g=1.5,highpass=f=65,lowpass=f=8500",
    "-c:a", "pcm_s16le", str(OUT),
], check=True)
print({"path": str(OUT), "voice": "M4", "pitch_shift": "-8%", "speed": 0.72})
