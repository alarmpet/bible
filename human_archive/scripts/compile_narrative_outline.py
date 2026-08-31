from __future__ import annotations

import argparse
from pathlib import Path

from human_archive.scripts.lib.narrative_outline import build_story_evidence_packet, compile_narrative_outline


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-snapshot", required=True, type=Path)
    parser.add_argument("--claims", required=True, type=Path)
    parser.add_argument("--policy", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    packet = build_story_evidence_packet(args.source_snapshot, args.claims, args.policy)
    compile_narrative_outline(packet, args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
