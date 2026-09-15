# -*- coding: utf-8 -*-
"""Test helpers and dataclasses for pipeline hardening v2."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any
import json
import yaml


@dataclass
class ApprovedBundlePaths:
    script: Path
    claim_inventory: Path
    source_snapshots: Path
    fact_report: Path
    persona_report: Path
    approval: Path
    shot_plan: Path
    shot_plan_approval: Path
    output: Path

    @property
    def artifacts(self) -> dict[str, Path]:
        return {
            "script_sha256": self.script,
            "claim_inventory_sha256": self.claim_inventory,
            "source_snapshot_sha256": self.source_snapshots,
            "fact_report_sha256": self.fact_report,
            "persona_report_sha256": self.persona_report,
        }

    def as_kwargs(self) -> dict[str, Path]:
        return {
            "shot_plan_path": self.shot_plan,
            "script_path": self.script,
            "claim_inventory_path": self.claim_inventory,
            "fact_report_path": self.fact_report,
            "persona_report_path": self.persona_report,
            "approval_path": self.approval,
            "shot_plan_approval_path": self.shot_plan_approval,
            "output_path": self.output,
        }


def make_valid_evidence_package() -> tuple[dict[str, Any], dict[str, Any]]:
    ledger = {
        "schema_version": 2,
        "episode_id": "EP01",
        "sources": [
            {
                "source_id": "SRC-PLINY",
                "title": "Epistles 6.16",
                "author_or_agency": "Pliny the Younger",
                "year": 105,
                "source_type": "primary_source",
                "peer_reviewed": False,
                "evidence_spans": [
                    {
                        "span_id": "SRC-PLINY:SPAN-01",
                        "locator": "Epistles 6.16.4",
                        "excerpt": "Nubes oriebatur...",
                        "excerpt_language": "la",
                        "translation": "소나무 모양 구름이 솟아올랐다.",
                        "translation_credit": "표준 번역",
                        "capture_method": "manual_verified_excerpt",
                        "captured_at_utc": "2026-08-21T00:00:00Z",
                        "snapshot_sha256": "A" * 64,
                    }
                ],
            },
            {
                "source_id": "SRC-INGV",
                "title": "INGV Vesuvius Report",
                "author_or_agency": "INGV",
                "year": 2022,
                "source_type": "official_agency",
                "peer_reviewed": False,
                "evidence_spans": [
                    {
                        "span_id": "SRC-INGV:SPAN-01",
                        "locator": "Page 12, Table 3",
                        "excerpt": "PDC dynamics...",
                        "excerpt_language": "it",
                        "translation": "화쇄류 모델링",
                        "translation_credit": "자체 번역",
                        "capture_method": "manual_verified_excerpt",
                        "captured_at_utc": "2026-08-21T00:00:00Z",
                        "snapshot_sha256": "B" * 64,
                    }
                ],
            },
        ],
        "claims": [
            {
                "claim_id": "CLM-001",
                "statement": "소 플리니우스는 소나무 구름을 관찰했다.",
                "type": "verified_fact",
                "risk": "low",
                "source_ids": ["SRC-PLINY"],
                "evidence_refs": ["SRC-PLINY:SPAN-01"],
                "approved_paraphrases": ["소 플리니우스는 미세눔에서 거대한 소나무 모양 구름을 목격했습니다."],
                "allowed_wording": ["소나무 구름", "목격"],
                "forbidden_wording": ["모든 시민 몰살"],
            }
        ],
    }

    snapshots = {
        "schema_version": 2,
        "episode_id": "EP01",
        "sources": ledger["sources"],
    }
    return ledger, snapshots
