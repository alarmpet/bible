import json
import shutil
import sys
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))
from build_tts_batch_jobs import build_batches  # noqa: E402

ROOT = Path(__file__).resolve().parent / "_tts_batch_fixture"


def test_tts_batches_preserve_scene_order_and_metadata():
    ROOT.mkdir(exist_ok=True)
    source = ROOT / "source"
    dest = ROOT / "batches"
    source.mkdir(exist_ok=True)
    try:
        scenes = [{"scene_id": f"s{i}", "narration": f"text{i}"} for i in range(1, 6)]
        (source / "scenes.json").write_text(json.dumps(scenes), encoding="utf-8")
        (source / "voice_map.json").write_text("{}", encoding="utf-8")
        outputs = build_batches(source, dest, batch_size=2)
        assert len(outputs) == 3
        assert json.loads((outputs[0] / "scenes.json").read_text(encoding="utf-8"))[0]["scene_id"] == "s1"
        assert json.loads((outputs[2] / "scenes.json").read_text(encoding="utf-8"))[0]["scene_id"] == "s5"
    finally:
        shutil.rmtree(ROOT, ignore_errors=True)
