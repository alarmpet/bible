"""Render a verified pilot from an explicit approved render manifest.

This entrypoint intentionally has no image discovery or fallback/reuse behavior.
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path
from flow_automation.native_host.render_runner import postflight_video, render_verified

def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--render-manifest', type=Path, required=True)
    parser.add_argument('--subtitle', type=Path, required=True)
    parser.add_argument('--audio', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--postflight-json', type=Path)
    args = parser.parse_args()
    render_manifest = json.loads(args.render_manifest.read_text(encoding='utf-8'))
    output = render_verified(render_manifest, args.subtitle, args.audio, args.output)
    report = postflight_video(output)
    if args.postflight_json:
        args.postflight_json.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    if report['status'] != 'PASS':
        raise SystemExit('postflight QA failed')
    print(output)
    return 0

if __name__ == '__main__':
    raise SystemExit(main())
