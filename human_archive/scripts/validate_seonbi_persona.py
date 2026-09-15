# -*- coding: utf-8 -*-
"""Validate ShipSeonbi persona, signature voice, and 5-stage story structure."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
import yaml

_SCRIPTS_DIR = Path(__file__).resolve().parent
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))

from lib.persona_validation import validate_persona

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--script", required=True, type=Path)
    parser.add_argument("--policy", type=Path)
    parser.add_argument("--audio-manifest", type=Path)
    parser.add_argument("--report", type=Path)
    args = parser.parse_args()

    script_data = json.loads(args.script.read_text(encoding="utf-8"))
    policy_path = args.policy or (_SCRIPTS_DIR.parent / "config" / "seonbi_narration_policy.yaml")
    policy_data = yaml.safe_load(policy_path.read_text(encoding="utf-8"))

    audio_manifest = None
    if args.audio_manifest and args.audio_manifest.exists():
        audio_manifest = json.loads(args.audio_manifest.read_text(encoding="utf-8"))

    report = validate_persona(script_data, policy_data, audio_manifest)

    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")

    if report["overall_status"] == "FAIL":
        print("❌ Persona Validation FAILED:")
        for err in report["errors"]:
            print(f"  - {err}")
        sys.exit(1)

    print(f"✅ Persona Validation Status: {report['overall_status']}")
    sys.exit(0)


if __name__ == "__main__":
    main()
