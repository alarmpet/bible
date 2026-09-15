# -*- coding: utf-8 -*-
"""Record episode KPI metrics and trigger retention feedback loops."""
from __future__ import annotations

import argparse
import csv
from datetime import datetime, timezone
from pathlib import Path
import sys
import yaml

_SCRIPTS_DIR = Path(__file__).resolve().parent
_ROOT = _SCRIPTS_DIR.parent
DEFAULT_CSV_PATH = _ROOT / "analytics" / "episode_metrics.csv"
DEFAULT_CONFIG_PATH = _ROOT / "config" / "channel_kpis.yaml"

COLUMNS = [
    "episode_id",
    "build_id",
    "format_profile",
    "published_at",
    "impressions_ctr",
    "retention_15s",
    "retention_30s",
    "average_percentage_viewed",
    "fact_corrections_count",
    "policy_failures",
]


def record_kpi(
    episode_id: str,
    build_id: str,
    format_profile: str,
    retention_15s: float,
    retention_30s: float,
    average_percentage_viewed: float,
    impressions_ctr: float = 0.0,
    fact_corrections_count: int = 0,
    policy_failures: int = 0,
    published_at: str | None = None,
    csv_path: Path = DEFAULT_CSV_PATH,
    config_path: Path = DEFAULT_CONFIG_PATH,
) -> dict:
    csv_path = Path(csv_path)
    config_path = Path(config_path)

    if not published_at:
        published_at = datetime.now(timezone.utc).isoformat()

    row = {
        "episode_id": episode_id,
        "build_id": build_id,
        "format_profile": format_profile,
        "published_at": published_at,
        "impressions_ctr": f"{impressions_ctr:.4f}",
        "retention_15s": f"{retention_15s:.4f}",
        "retention_30s": f"{retention_30s:.4f}",
        "average_percentage_viewed": f"{average_percentage_viewed:.4f}",
        "fact_corrections_count": str(fact_corrections_count),
        "policy_failures": str(policy_failures),
    }

    # Read existing
    rows = []
    if csv_path.exists():
        with open(csv_path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            rows = list(reader)

    # Check update or append
    matched = False
    for i, r in enumerate(rows):
        if r.get("episode_id") == episode_id and r.get("build_id") == build_id:
            rows[i] = row
            matched = True
            break
    if not matched:
        rows.append(row)

    csv_path.parent.mkdir(parents=True, exist_ok=True)
    with open(csv_path, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=COLUMNS)
        writer.writeheader()
        writer.writerows(rows)

    # Evaluate KPI alert triggers
    alert = None
    if config_path.exists():
        cfg = yaml.safe_load(config_path.read_text(encoding="utf-8"))
        kpis = cfg.get("kpis", {})
        target_30s = kpis.get("retention_30s_target", 0.55)
        drop_thresh = kpis.get("hook_review_drop_threshold", 0.20)

        if retention_30s < (target_30s - drop_thresh):
            alert = f"⚠️ ALERT: retention_30s ({retention_30s:.2%}) dropped more than {drop_thresh:.0%}p below target ({target_30s:.2%}). Hook review required for next episode script!"

    return {
        "status": "recorded",
        "row": row,
        "alert": alert,
    }


def main():
    parser = argparse.ArgumentParser(description="Record episode KPI metric")
    parser.add_argument("--episode-id", required=True)
    parser.add_argument("--build-id", required=True)
    parser.add_argument("--format-profile", default="standard_docu")
    parser.add_argument("--retention-15s", type=float, required=True)
    parser.add_argument("--retention-30s", type=float, required=True)
    parser.add_argument("--apv", type=float, required=True, help="Average percentage viewed (0.0 - 1.0)")
    parser.add_argument("--ctr", type=float, default=0.0)
    parser.add_argument("--corrections", type=int, default=0)
    parser.add_argument("--policy-failures", type=int, default=0)
    parser.add_argument("--csv", type=Path, default=DEFAULT_CSV_PATH)
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG_PATH)
    args = parser.parse_args()

    res = record_kpi(
        episode_id=args.episode_id,
        build_id=args.build_id,
        format_profile=args.format_profile,
        retention_15s=args.retention_15s,
        retention_30s=args.retention_30s,
        average_percentage_viewed=args.apv,
        impressions_ctr=args.ctr,
        fact_corrections_count=args.corrections,
        policy_failures=args.policy_failures,
        csv_path=args.csv,
        config_path=args.config,
    )
    print(f"✅ Recorded KPI for {args.episode_id} ({args.build_id})")
    if res.get("alert"):
        print(res["alert"])


if __name__ == "__main__":
    main()
