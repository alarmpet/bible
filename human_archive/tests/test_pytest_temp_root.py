import importlib.util
import os
import time
from pathlib import Path
import pytest

_ROOT_CONFTEST = Path(__file__).resolve().parents[2] / "conftest.py"
_spec = importlib.util.spec_from_file_location("root_conftest", _ROOT_CONFTEST)
_root_conftest = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_root_conftest)

_is_pid_alive_windows = _root_conftest._is_pid_alive_windows
_run_basetemp_garbage_collection = _root_conftest._run_basetemp_garbage_collection


def test_pytest_tmp_path_uses_d_drive_scratch(tmp_path: Path):
    assert tmp_path.drive.upper() == "D:"
    assert "pytest_tmp" in str(tmp_path).replace("\\", "/")


def test_pytest_tmp_path_isolation_uses_unique_session_directory(tmp_path: Path):
    assert tmp_path.parent.name.startswith("run_")


def test_is_pid_alive_windows():
    current_pid = os.getpid()
    assert _is_pid_alive_windows(current_pid) is True
    # Non-existent high PID
    assert _is_pid_alive_windows(9999999) is False
    assert _is_pid_alive_windows(-1) is False


def test_basetemp_garbage_collection(tmp_path: Path):
    dummy_root = tmp_path / "gc_test_root"
    dummy_root.mkdir()

    # Create 8 dummy dead sessions
    for i in range(8):
        sess = dummy_root / f"run_999999{i}_{time.time_ns()}"
        sess.mkdir()
        (sess / "dummy.txt").write_text("test")
        time.sleep(0.01)

    # Active session that should never be deleted
    active_sess = dummy_root / f"run_{os.getpid()}_{time.time_ns()}"
    active_sess.mkdir()

    # Run GC retaining 3 sessions
    _run_basetemp_garbage_collection(dummy_root, retain_count=3, ttl_seconds=86400.0)

    # Active session must survive
    assert active_sess.exists()

    # Total remaining sessions should be: active session + up to 3 retained dead sessions
    remaining = list(dummy_root.iterdir())
    assert len(remaining) <= 4

