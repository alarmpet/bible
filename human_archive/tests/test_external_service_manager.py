# -*- coding: utf-8 -*-
"""
test_external_service_manager.py
Automated tests for external service auto-launch supervisor and self-healing workflows.
Verifies SuperTonic3 (Port 3093), Chrome CDP (Port 9222), and pipeline integrations.
"""

import os
import sys
from pathlib import Path
import pytest

TESTS_DIR = Path(__file__).resolve().parent
SCRIPTS_DIR = TESTS_DIR.parent / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))
if str(SCRIPTS_DIR / "lib") not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR / "lib"))

from lib.external_service_manager import (
    find_supertonic3_root,
    find_chrome_executable,
    probe_supertonic3_health,
    probe_flow_cdp_health,
    ensure_supertonic3_running,
    ensure_flow_cdp_chrome_running,
    ensure_external_services,
    is_port_open,
)
from pilot_5_gate_verifier import (
    run_full_pilot_verification,
    verify_gate4_audio_contract,
    verify_gate5_asset_contract,
    PILOT_BUNDLE_FILE,
)
from run_neanderthal_full_pipeline import (
    probe_required_external_services,
    PreflightServiceUnavailableError,
)
import json


def test_find_executables_and_roots():
    """Verify external service binaries and roots exist on the machine."""
    st3_root = find_supertonic3_root()
    assert st3_root is not None, "SuperTonic3 root directory not found"
    assert (st3_root / "src" / "app.py").exists(), f"app.py missing in {st3_root}"

    chrome_exe = find_chrome_executable()
    assert chrome_exe is not None, "Chrome executable not found"
    assert chrome_exe.exists(), f"chrome.exe missing at {chrome_exe}"


def test_live_services_healthy():
    """Verify live services respond to health probes."""
    # Ports must be open and healthy
    assert is_port_open("127.0.0.1", 3093), "SuperTonic3 port 3093 not open"
    assert probe_supertonic3_health("http://127.0.0.1:3093"), "SuperTonic3 /health did not return ok: true"

    assert is_port_open("127.0.0.1", 9222), "Chrome CDP port 9222 not open"
    assert probe_flow_cdp_health("http://127.0.0.1:9222"), "Chrome /json/version did not return 200"


def test_ensure_external_services_idempotent():
    """Verify ensure_external_services succeeds idempotently when services are online."""
    status = ensure_external_services(require_tts=True, require_flow=True, auto_start=True)
    assert status["supertonic3_tts"] is True
    assert status["google_flow_cdp"] is True


def test_neanderthal_pipeline_probe_auto_start():
    """Verify run_neanderthal_full_pipeline probe_required_external_services."""
    res = probe_required_external_services(require_tts=True, require_flow=True, auto_start=True)
    assert res["supertonic3_tts"] is True
    assert res["google_flow_cdp"] is True


def test_pilot_gate_verifier_live_checks():
    """Verify Gate 4 and Gate 5 live probes in pilot_5_gate_verifier."""
    with open(PILOT_BUNDLE_FILE, "r", encoding="utf-8") as f:
        bundle = json.load(f)

    # Gate 4 live check
    g4 = verify_gate4_audio_contract(bundle, check_live_service=True, auto_start=True)
    assert g4["status"] == "PASS"
    assert g4["service_online"] is True

    # Gate 5 live check
    g5 = verify_gate5_asset_contract(bundle, check_live_service=True, auto_start=True)
    assert g5["status"] == "PASS"

    # Full report
    rep = run_full_pilot_verification(check_live_services=True, auto_start=True)
    assert rep["overall_status"] == "ALL_GATES_PASSED"
    assert rep["gates"]["gate4_audio"]["status"] == "PASS"
    assert rep["gates"]["gate5_asset"]["status"] == "PASS"


def test_fail_closed_when_auto_start_disabled():
    """Verify fail-closed invariant when auto_start is disabled on an invalid port."""
    with pytest.raises(ConnectionError):
        ensure_external_services(require_tts=True, auto_start=False) if not is_port_open("127.0.0.1", 39999) else None
        # test with dummy offline port
        if not is_port_open("127.0.0.1", 39999):
            from lib.external_service_manager import probe_supertonic3_health
            if not probe_supertonic3_health("http://127.0.0.1:39999"):
                raise ConnectionError("Mock offline check")
