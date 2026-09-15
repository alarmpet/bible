# -*- coding: utf-8 -*-
"""Test generic script generation and provider output parsing."""
from __future__ import annotations

import json
import sys
from pathlib import Path
import pytest
import yaml

_TEST_DIR = Path(__file__).resolve().parent
_PROJECT_ROOT = _TEST_DIR.parents[1]
_SCRIPTS_DIR = _PROJECT_ROOT / "human_archive" / "scripts"
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))

from unittest.mock import patch, MagicMock
from lib.script_generation import AntigravityCliProvider, JsonFileProvider, OmniRouteProvider, generate_script_candidate


@pytest.fixture
def generic_inputs():
    c_path = _PROJECT_ROOT / "human_archive" / "tests" / "fixtures" / "episode_generic_v2.yaml"
    contract = yaml.safe_load(c_path.read_text(encoding="utf-8"))
    inventory = {
        "schema_version": 2,
        "episode_id": "GENERIC-002",
        "claims": [
            {
                "claim_id": "CLM-GEN-001",
                "statement": "도서관은 수세기에 걸쳐 점진적으로 쇠퇴했다.",
                "risk": "low",
                "evidence_refs": ["SRC-GEN-01:SPAN-01"],
                "allowed_wording": ["점진적 쇠퇴"],
                "forbidden_wording": ["단 하룻밤 소실"],
            }
        ],
    }
    snapshots = {
        "schema_version": 2,
        "episode_id": "GENERIC-002",
        "sources": [
            {
                "source_id": "SRC-GEN-01",
                "title": "Alexandria Studies",
                "evidence_spans": [{"span_id": "SRC-GEN-01:SPAN-01"}],
            }
        ],
    }
    pol_path = _PROJECT_ROOT / "human_archive" / "config" / "seonbi_narration_policy.yaml"
    policy = yaml.safe_load(pol_path.read_text(encoding="utf-8"))
    return contract, inventory, snapshots, policy


def test_generic_generation_uses_contract_and_not_pompeii_constants(generic_inputs):
    provider = JsonFileProvider(_PROJECT_ROOT / "human_archive" / "tests" / "fixtures" / "script_candidate_v2.json")
    script = generate_script_candidate(*generic_inputs, provider=provider)
    assert script["episode_id"] == "GENERIC-002"
    assert script["persona"] == "ship_seonbi"
    assert "폼페이" not in json.dumps(script, ensure_ascii=False)


def test_antigravity_cli_provider_with_fixture(generic_inputs):
    fixture_path = _PROJECT_ROOT / "human_archive" / "tests" / "fixtures" / "script_candidate_v2.json"
    provider = AntigravityCliProvider(response_path=fixture_path)
    script = generate_script_candidate(*generic_inputs, provider=provider)
    assert script["episode_id"] == "GENERIC-002"
    assert script["persona"] == "ship_seonbi"


def test_omniroute_provider_connection_error_handling():
    provider = OmniRouteProvider(base_url="http://invalid-localhost-port-99999/v1", timeout_sec=0.1)
    with pytest.raises(ConnectionError, match="Failed to connect to gateway"):
        provider.generate(prompt="test", output_schema={})


def test_omniroute_provider_mocked_generation(generic_inputs):
    fixture_script = json.loads((_PROJECT_ROOT / "human_archive" / "tests" / "fixtures" / "script_candidate_v2.json").read_text(encoding="utf-8"))
    mock_resp = MagicMock()
    mock_resp.json.return_value = {
        "choices": [
            {
                "message": {
                    "content": json.dumps(fixture_script)
                }
            }
        ]
    }
    with patch("requests.post", return_value=mock_resp) as mock_post:
        provider = OmniRouteProvider(base_url="http://localhost:20128/v1", model="auto")
        script = generate_script_candidate(*generic_inputs, provider=provider)
        assert script["episode_id"] == "GENERIC-002"
        mock_post.assert_called_once()
        args, kwargs = mock_post.call_args
        assert args[0] == "http://localhost:20128/v1/chat/completions"
        assert kwargs["json"]["model"] == "auto"



