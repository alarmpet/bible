"""Render a bounded scene range so long jobs can resume safely."""
from __future__ import annotations

import argparse
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from render_simple_longform import FFMPEG, render_scene  # noqa: E402


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--job", required=True)
    ap.add_argument("--start", type=int, required=True)
    ap.add_argument("--end", type=int, required=True)
    ap.add_argument("--workers", type=int, default=4)
    args = ap.parse_args()
    job = Path(args.job).resolve()
    orders = list(range(args.start, args.end + 1))
    failures = []
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        futures = {pool.submit(render_scene, job, order, str(FFMPEG)): order for order in orders}
        for future in as_completed(futures):
            order = futures[future]
            try:
                future.result()
            except Exception as exc:
                failures.append({"order": order, "error": str(exc)})
    print({"ok": not failures, "start": args.start, "end": args.end, "rendered": len(orders) - len(failures), "failures": failures})
    if failures:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
