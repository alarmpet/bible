# -*- coding: utf-8 -*-
"""Pytest configuration and shared fixtures for human_archive tests."""
from __future__ import annotations

import sys
import importlib.util
from pathlib import Path
import pytest
import yaml

_TEST_DIR = Path(__file__).resolve().parent
_PROJECT_ROOT = _TEST_DIR.parents[1]
_SCRIPTS_DIR = _PROJECT_ROOT / "human_archive" / "scripts"
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))

# pytest.ini lives under human_archive/, so pytest does not discover the
# repository-level conftest.py in D:\module\bible. Load its session isolation
# hook explicitly to preserve the documented D:\module\scratch\pytest_tmp\run_*
# contract for both local and CI invocations.
_ROOT_CONFTEST = _PROJECT_ROOT / "conftest.py"
_ROOT_SPEC = importlib.util.spec_from_file_location("human_archive_root_conftest", _ROOT_CONFTEST)
_ROOT_MODULE = importlib.util.module_from_spec(_ROOT_SPEC)
assert _ROOT_SPEC.loader is not None
_ROOT_SPEC.loader.exec_module(_ROOT_MODULE)

from helpers_v2 import make_valid_evidence_package


def pytest_configure(config) -> None:
    _ROOT_MODULE.pytest_configure(config)


@pytest.fixture
def profile_config():
    p_path = _PROJECT_ROOT / "human_archive" / "config" / "delivery_profiles.yaml"
    if not p_path.exists():
        return {}
    return yaml.safe_load(p_path.read_text(encoding="utf-8"))


@pytest.fixture
def valid_evidence():
    return make_valid_evidence_package()
