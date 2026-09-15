from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
REJECTED = ROOT / "human_archive" / "runs" / "ep02_jang_huibin" / "full-v4-001"
REBUILT = ROOT / "human_archive" / "runs" / "ep02_jang_huibin" / "full-v4-002"


def test_rejected_build_preserves_the_known_prompt_failure_evidence():
    prompts = json.loads((REJECTED / "flow_image_prompts.json").read_text(encoding="utf-8"))
    report = json.loads((REJECTED / "visual_failure_report.json").read_text(encoding="utf-8"))
    host_count = sum(
        "main character is" in item["prompt"].lower()
        or "seonbi stickman" in item["prompt"].lower()
        for item in prompts
    )
    year_count = sum("1701" in item["prompt"] for item in prompts)
    assert report["status"] == "REJECTED"
    assert report["release_eligible"] is False
    assert host_count == len(prompts)
    assert year_count == len(prompts)


def test_rebuilt_prompts_do_not_force_host_or_literal_year():
    prompts = json.loads((REBUILT / "flow_image_prompts.json").read_text(encoding="utf-8"))
    host_count = sum(item["visual_role"] == "host_explainer" for item in prompts)
    assert 0.15 <= host_count / len(prompts) <= 0.25
    assert all("1701" not in item["prompt"] for item in prompts)
    assert all(not any(character.isdigit() for character in item["prompt"]) for item in prompts)
    assert all(
        item["host_mode"] == ("full" if item["visual_role"] == "host_explainer" else "absent")
        for item in prompts
    )


def test_rebuilt_role_prompts_block_collages_hands_and_second_presenters():
    manifest = json.loads((REBUILT / "image_request_manifest.json").read_text(encoding="utf-8"))
    requests = manifest["requests"]
    hosts = [item for item in requests if item["visual_role"] == "host_explainer"]
    evidence = [item for item in requests if item["visual_role"] == "evidence_object"]
    assert len(hosts) == 13
    assert len(evidence) == 27
    for item in hosts:
        prompt = item["submission_prompt"].lower()
        assert "presenter points" not in prompt
        assert "no people" in prompt
        assert "no hands" in prompt
        assert "no human body parts" in prompt
        assert "single coherent vignette" in prompt
        assert {"additional person", "disembodied hand", "collage", "catalogue sheet"} <= set(
            item["negative"]["items"]
        )
    for item in evidence:
        prompt = item["submission_prompt"].lower()
        assert "royal court clothing and architecture" not in prompt
        assert "filled editorial" not in prompt
        assert "hands examine" not in prompt
        assert "historical figures take part" not in prompt
        assert "historical figures perform" not in prompt
        assert "restrained royal council debate" not in prompt
