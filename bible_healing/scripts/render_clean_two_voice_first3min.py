import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
import render_actual_first3min_locked as base

base.JOB=Path(r"C:\Users\amd\module\bible_healing\runs\ep01_anxious_night\hermes_jobs\actual_first3min_clean_two_voice")
base.BG=Path(r"C:\Users\amd\module\bible_healing\runs\ep01_anxious_night\hermes_jobs\voice_pastor_calm_M4\locked_voice_slow333")
base.OUT=base.JOB/"final-first3min-clean-two-voice-slow0333.mp4"
base.WORK=base.JOB/"render_work"
base.WORK.mkdir(exist_ok=True)
base.main()
