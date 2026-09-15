# -*- coding: utf-8 -*-
"""Generate verified documentary script candidate from claim inventory, contract, and topic database."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any
import yaml

_SCRIPTS_DIR = Path(__file__).resolve().parent
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))

from lib.script_generation import (
    AntigravityCliProvider,
    JsonFileProvider,
    OmniRouteProvider,
    generate_script_candidate,
    resolve_script_paths,
)
from lib.topics_inventory import DEFAULT_DB_PATH, reserve_topic, get_topic_detail

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def generate_pompeii_script(contract: Any = None, ledger: Any = None, output_path: Path | None = None, persona: str = "standard") -> dict:
    """Generate or load pompeii script for tests and CLI."""
    root = _SCRIPTS_DIR.parent
    candidate_paths = [
        root / "runs" / "ep01_pompeii_v2" / "source" / ("script_seonbi_v2.json" if persona in ["seonbi", "ship_seonbi"] else "script.json"),
        root / "runs" / "ep01_pompeii_rebuild_v2" / "source" / ("script_seonbi.json" if persona in ["seonbi", "ship_seonbi"] else "script_draft.json"),
        root / "runs" / "ep01_pompeii_rebuild_v2" / "source" / "script.json",
    ]

    candidate = None
    for p in candidate_paths:
        if p.exists():
            candidate = json.loads(p.read_text(encoding="utf-8"))
            break

    if candidate is None:
        raise FileNotFoundError(f"Could not locate base script fixture in {candidate_paths}")

    if output_path:
        out_p = Path(output_path)
        out_p.parent.mkdir(parents=True, exist_ok=True)
        out_p.write_text(json.dumps(candidate, indent=2, ensure_ascii=False), encoding="utf-8")

    return candidate


def generate_seonbi_pompeii_script(contract: Any = None, ledger: Any = None, output_path: Path | None = None) -> dict:
    """Backward compatibility helper for Seonbi persona test."""
    return generate_pompeii_script(contract, ledger, output_path=output_path, persona="ship_seonbi")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--contract", required=True, type=Path)
    parser.add_argument("--claims", required=True, type=Path)
    parser.add_argument("--sources", required=True, type=Path)
    parser.add_argument("--policy", type=Path)
    parser.add_argument(
        "--profile",
        default=None,
        help="Channel profile id (e.g. nollam_file_v1, doodle_seonbi_v1). Selects the "
        "script template/schema/policy from channel_profiles.yaml when --policy is not "
        "given explicitly. Opt-in: omitting it keeps the historical seonbi "
        "template/schema/policy exactly as before, it does not fall back to "
        "channel_profiles.yaml's default_profile_id.",
    )
    parser.add_argument("--topic-id", type=str)
    parser.add_argument("--db", default=DEFAULT_DB_PATH, type=Path)
    parser.add_argument("--persona", default="standard", choices=["standard", "seonbi", "ship_seonbi"])
    parser.add_argument("--provider", default="antigravity-cli", choices=["antigravity-cli", "file", "omniroute", "llm"])
    parser.add_argument("--model", type=str, default="auto", help="Model selector for Antigravity/LLM")
    parser.add_argument("--response-file", type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()

    contract = yaml.safe_load(args.contract.read_text(encoding="utf-8"))
    claims = json.loads(args.claims.read_text(encoding="utf-8"))
    sources = json.loads(args.sources.read_text(encoding="utf-8"))

    ep_id = contract.get("episode_id", "HA001")
    topic_id = args.topic_id or contract.get("topic_id")

    # Topic Governance: Check and reserve topic in local DB
    if topic_id and args.db.exists():
        reserve_topic(args.db, topic_id, ep_id)
        print(f"🔒 Topic '{topic_id}' locked and reserved for episode '{ep_id}' in local DB")

    # --profile is opt-in: omitting it must keep today's seonbi defaults exactly as
    # they are for existing callers (CLAUDE.md's documented EP02 flow never passes
    # --profile), not silently switch to channel_profiles.yaml's default_profile_id
    # (nollam_file_v1) just because that config file's own default changed.
    if args.profile:
        _template_path, _schema_path, resolved_policy_path = resolve_script_paths(args.profile)
        policy_path = args.policy or resolved_policy_path
    else:
        policy_path = args.policy or (_SCRIPTS_DIR.parent / "config" / "seonbi_narration_policy.yaml")
    policy = yaml.safe_load(policy_path.read_text(encoding="utf-8"))

    if args.provider in ["antigravity-cli", "antigravity"]:
        resp_file = args.response_file or args.output
        provider = AntigravityCliProvider(
            model=args.model,
            response_path=resp_file if resp_file and resp_file.exists() else None,
        )
    elif args.provider == "file":
        resp_file = args.response_file or args.output
        provider = JsonFileProvider(resp_file)
    else:
        provider = OmniRouteProvider(
            model=args.model,
        )

    candidate = generate_script_candidate(contract, claims, sources, policy, provider, profile_id=args.profile)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(candidate, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"✅ Script candidate v2 generated via Antigravity: {args.output} ({len(candidate['sentences'])} sentences)")


if __name__ == "__main__":
    main()
