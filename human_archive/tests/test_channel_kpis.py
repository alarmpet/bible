# -*- coding: utf-8 -*-
"""Test channel KPI calibration and CSV schema validation."""
from __future__ import annotations

import csv
import sys
from pathlib import Path
import pytest
import yaml

_TEST_DIR = Path(__file__).resolve().parent
_PROJECT_ROOT = _TEST_DIR.parents[1]


def test_channel_kpis_exact_csv_columns():
    csv_path = _PROJECT_ROOT / "human_archive" / "analytics" / "episode_metrics.csv"
    assert csv_path.exists()

    with open(csv_path, "r", encoding="utf-8") as f:
        reader = csv.reader(f)
        header = next(reader)

    expected_cols = [
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
    assert header == expected_cols


def test_channel_kpi_configuration():
    kpi_path = _PROJECT_ROOT / "human_archive" / "config" / "channel_kpis.yaml"
    assert kpi_path.exists()
    cfg = yaml.safe_load(kpi_path.read_text(encoding="utf-8"))
    assert cfg["calibration_episodes_count"] == 5
    assert cfg["snapshots_days"] == [7, 28]


def test_record_kpi_appends_and_triggers_retention_alert(tmp_path: Path):
    _SCRIPTS_DIR = _PROJECT_ROOT / "human_archive" / "scripts"
    if str(_SCRIPTS_DIR) not in sys.path:
        sys.path.insert(0, str(_SCRIPTS_DIR))
    from record_episode_kpi import record_kpi

    tmp_csv = tmp_path / "metrics.csv"
    tmp_cfg = tmp_path / "kpis.yaml"
    tmp_cfg.write_text(
        yaml.dump({
            "kpis": {
                "retention_30s_target": 0.55,
                "hook_review_drop_threshold": 0.20,
            }
        }),
        encoding="utf-8",
    )

    # 1. Normal record (no alert)
    res1 = record_kpi(
        episode_id="HA001",
        build_id="b-01",
        format_profile="standard_docu",
        retention_15s=0.72,
        retention_30s=0.58,
        average_percentage_viewed=0.45,
        csv_path=tmp_csv,
        config_path=tmp_cfg,
    )
    assert res1["status"] == "recorded"
    assert res1["alert"] is None

    # 2. Low retention record (triggers alert)
    res2 = record_kpi(
        episode_id="HA002",
        build_id="b-01",
        format_profile="standard_docu",
        retention_15s=0.40,
        retention_30s=0.30,  # 30% is 25%p below 55%
        average_percentage_viewed=0.20,
        csv_path=tmp_csv,
        config_path=tmp_cfg,
    )
    assert res2["status"] == "recorded"
    assert res2["alert"] is not None
    assert "Hook review required" in res2["alert"]

