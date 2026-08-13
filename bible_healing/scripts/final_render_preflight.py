"""Fail-fast checks required before a final render."""
from pathlib import Path
import json, re, sys

ROOT = Path(__file__).resolve().parents[2]
POLICY = ROOT / "bible_healing/config/final_render_policy.json"
JOB = ROOT / "bible_healing/runs/ep01_anxious_night/hermes_jobs/actual_first3min_pause_split"

def main():
    policy = json.loads(POLICY.read_text(encoding="utf-8"))
    scenes = json.loads((JOB / "scenes.json").read_text(encoding="utf-8"))
    allowed = set(policy["speakers"])
    bad = []
    segment_count = 0
    for scene in scenes:
        for seg in scene.get("segments", []):
            segment_count += 1
            speaker = seg.get("speaker")
            text = (seg.get("text") or "").strip()
            if speaker not in allowed:
                bad.append(f"speaker:{speaker}")
            if not text:
                bad.append(f"empty:{seg.get('seg_id')}")
            if speaker == "scripture":
                if re.search(r"[()]|셀라|첼라|다윗의 시|영장으로|!", text):
                    bad.append(f"unclean_scripture:{seg.get('seg_id')}")
            wav = JOB / "segments" / f"{seg.get('seg_id')}_{speaker}_{'M4' if speaker == 'scripture' else 'F5'}.wav"
            if not wav.exists():
                bad.append(f"missing_audio:{wav.name}")
    print(json.dumps({"policy": str(POLICY), "segments": segment_count, "errors": bad}, ensure_ascii=False))
    return 1 if bad else 0

if __name__ == "__main__":
    sys.exit(main())
