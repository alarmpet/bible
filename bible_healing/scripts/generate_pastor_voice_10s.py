from pathlib import Path
import sys

ROOT = Path(r"C:\Users\amd\supertonic3-local-tts-20260517-r4\supertonic3-local-tts")
OUT = Path(r"C:\Users\amd\module\bible_healing\runs\ep01_anxious_night\voice_ab\pastor_calm_10s_M4.wav")
sys.path.insert(0, str(ROOT / "src"))
from supertonic3_engine import Supertonic3Engine

text = "오늘 밤, 잠시 모든 걱정을 내려놓으셔도 괜찮습니다. 하나님께서 지금 이 순간에도 당신 곁에 계십니다."
engine = Supertonic3Engine(output_dir=OUT.parent)
info = engine.synthesize_to_file(
    text=text,
    output_path=OUT,
    voice="M4",
    lang="ko",
    speed=0.72,
    total_step=24,
    silence_duration=0.65,
    verbose=False,
)
print({"path": str(OUT), "duration": info.get("duration"), "voice": "M4", "speed": 0.72, "silence": 0.65})
