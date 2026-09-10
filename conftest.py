"""Project-wide pytest isolation for Windows media-heavy test runs."""

from __future__ import annotations

import os
import shutil
import time
from pathlib import Path


def _is_pid_alive_windows(pid: int) -> bool:
    """Windows 환경에서 특정 PID의 프로세스가 여전히 실행 중인지 안전하게 검사."""
    if pid <= 0:
        return False
    try:
        import ctypes
        kernel32 = ctypes.windll.kernel32
        PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
        h_process = kernel32.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False, pid)
        if h_process:
            kernel32.CloseHandle(h_process)
            return True
        return False
    except Exception:
        try:
            os.kill(pid, 0)
            return True
        except OSError:
            return False


def _run_basetemp_garbage_collection(
    root: Path,
    retain_count: int = 5,
    ttl_seconds: float = 86400.0,
) -> None:
    """이전 pytest 세션 디렉터리를 안전하게 청소하는 TTL & Retain-K GC 엔진."""
    if not root.exists():
        return

    now = time.time()
    candidates: list[tuple[Path, float, int]] = []

    for entry in root.iterdir():
        if not entry.is_dir():
            continue
        name = entry.name
        if not name.startswith("run_"):
            candidates.append((entry, entry.stat().st_mtime, 0))
            continue

        parts = name.split("_")
        pid = 0
        if len(parts) >= 3:
            try:
                pid = int(parts[1])
                # 현재 살아있는 프로세스의 디렉터리는 절대 건드리지 않음
                if _is_pid_alive_windows(pid):
                    continue
            except ValueError:
                pid = 0
        candidates.append((entry, entry.stat().st_mtime, pid))

    # 최신 수정 시간 순 정렬 (최신 것이 앞)
    candidates.sort(key=lambda x: x[1], reverse=True)

    # 상위 retain_count개는 보존, 그 이후 및 TTL 초과 디렉터리 삭제
    for idx, (path, mtime, _) in enumerate(candidates):
        is_stale_by_count = idx >= retain_count
        is_stale_by_ttl = (now - mtime) > ttl_seconds

        if is_stale_by_count or is_stale_by_ttl:
            try:
                shutil.rmtree(path, ignore_errors=True)
            except Exception:
                pass


def pytest_configure(config) -> None:
    """Give every pytest process a private D: basetemp directory and GC stale sessions.

    The command-line default remains a stable parent for disk policy checks, but
    each process gets a unique child so delayed Windows file-handle release from
    a previous run cannot collide with the next run.
    """
    root = Path(r"D:\module\scratch\pytest_tmp")
    root.mkdir(parents=True, exist_ok=True)

    try:
        _run_basetemp_garbage_collection(root, retain_count=5, ttl_seconds=86400.0)
    except Exception:
        pass

    session_dir = root / f"run_{os.getpid()}_{time.time_ns()}"
    config.option.basetemp = str(session_dir)

