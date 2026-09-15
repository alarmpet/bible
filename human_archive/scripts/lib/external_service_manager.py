# -*- coding: utf-8 -*-
"""
external_service_manager.py
Self-healing supervisor for external production services:
- SuperTonic3 TTS server (Port 3093)
- Google Chrome Remote Debugging for Flow CDP (Port 9222)

Enforces AGENTS.md clean workspace, fail-closed preflight, and automatic self-launch.
"""

from __future__ import annotations

import json
import os
import socket
import subprocess
import sys
import time
import urllib.request
import urllib.error
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

SCRIPTS_DIR = Path(__file__).resolve().parent.parent
LIB_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPTS_DIR.parent
SCRATCH_LOG_DIR = Path(r"D:\module\scratch\service_logs")

if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))
if str(LIB_DIR) not in sys.path:
    sys.path.insert(0, str(LIB_DIR))


def is_port_open(host: str = "127.0.0.1", port: int = 3093, timeout: float = 1.0) -> bool:
    """Check whether a TCP port is open and accepting connections."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(timeout)
        try:
            s.connect((host, port))
            return True
        except (socket.timeout, ConnectionRefusedError, OSError):
            return False


def find_supertonic3_root() -> Optional[Path]:
    """Locate SuperTonic3 local TTS repository root."""
    candidates = [
        os.environ.get("HERMES_TTS_ROOT"),
        str(Path.home() / "supertonic3-local-tts-20260517-r4" / "supertonic3-local-tts"),
        r"C:\Users\shs\supertonic3-local-tts-20260517-r4\supertonic3-local-tts",
        r"C:\Users\amd\supertonic3-local-tts-20260517-r4\supertonic3-local-tts",
    ]
    for c in candidates:
        if c:
            p = Path(c)
            if p.exists() and (p / "src" / "app.py").exists():
                return p
    return None


def find_chrome_executable() -> Optional[Path]:
    """Locate Google Chrome executable on Windows."""
    candidates = [
        Path(r"C:\Program Files\Google\Chrome\Application\chrome.exe"),
        Path(r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe"),
        Path.home() / "AppData" / "Local" / "Google" / "Chrome" / "Application" / "chrome.exe",
    ]
    for p in candidates:
        if p.exists():
            return p
    return None


def probe_supertonic3_health(base_url: str = "http://127.0.0.1:3093", timeout: float = 2.0) -> bool:
    """Check if SuperTonic3 HTTP server responds to /health."""
    url = f"{base_url.rstrip('/')}/health"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "ExternalServiceManager/1.0"})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            if resp.status != 200:
                return False
            payload = json.loads(resp.read().decode("utf-8"))
            return bool(payload.get("ok"))
    except Exception:
        return False


def probe_flow_cdp_health(base_url: str = "http://127.0.0.1:9222", timeout: float = 2.0) -> bool:
    """Check if Chrome Remote Debugging responds to /json/version."""
    url = f"{base_url.rstrip('/')}/json/version"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "ExternalServiceManager/1.0"})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.status == 200
    except Exception:
        return False


def ensure_supertonic3_running(
    port: int = 3093,
    host: str = "127.0.0.1",
    max_wait_sec: float = 25.0,
    force_restart: bool = False,
) -> bool:
    """Ensure SuperTonic3 TTS server is running and healthy. Auto-starts if offline."""
    base_url = f"http://{host}:{port}"
    if not force_restart and probe_supertonic3_health(base_url):
        return True

    root = find_supertonic3_root()
    if not root:
        raise FileNotFoundError(
            "Cannot auto-launch SuperTonic3: repository root not found. "
            "Please check HERMES_TTS_ROOT or install location."
        )

    python_exe = root / ".venv-win" / "Scripts" / "python.exe"
    if not python_exe.exists():
        python_exe = Path(sys.executable)

    app_py = root / "src" / "app.py"
    if not app_py.exists():
        raise FileNotFoundError(f"SuperTonic3 app entry point missing: {app_py}")

    SCRATCH_LOG_DIR.mkdir(parents=True, exist_ok=True)
    log_file = SCRATCH_LOG_DIR / "supertonic3_server.log"

    env = os.environ.copy()
    env["PYTHONPATH"] = str(root / "src")
    env["SUPERTONIC3_HOST"] = host
    env["SUPERTONIC3_PORT"] = str(port)

    # Windows detached background process creation
    creationflags = 0
    if sys.platform == "win32":
        creationflags = subprocess.CREATE_NEW_PROCESS_GROUP | 0x00000008  # DETACHED_PROCESS

    print(f"[*] Auto-launching SuperTonic3 server on {base_url} (root: {root})...")
    if sys.platform == "win32":
        ps_cmd = (
            f"$env:PYTHONPATH = '{root / 'src'}'; "
            f"$env:SUPERTONIC3_HOST = '{host}'; "
            f"$env:SUPERTONIC3_PORT = '{port}'; "
            f"Start-Process -FilePath '{python_exe}' -ArgumentList '{app_py}' -WorkingDirectory '{root}' -WindowStyle Hidden"
        )
        subprocess.run(["powershell", "-NoProfile", "-Command", ps_cmd], check=False)
    else:
        with open(log_file, "a", encoding="utf-8") as out_f:
            subprocess.Popen(
                [str(python_exe), str(app_py)],
                cwd=str(root),
                env=env,
                stdout=out_f,
                stderr=subprocess.STDOUT,
                close_fds=True,
            )

    # Poll until server responds to /health
    start_time = time.time()
    while time.time() - start_time < max_wait_sec:
        if probe_supertonic3_health(base_url, timeout=1.0):
            print(f"[+] SuperTonic3 server is ONLINE at {base_url}")
            return True
        time.sleep(0.5)

    raise TimeoutError(
        f"SuperTonic3 failed to respond to /health within {max_wait_sec}s. "
        f"Check log file at {log_file}."
    )


def ensure_flow_cdp_chrome_running(
    port: int = 9222,
    target_url: str = "https://labs.google/fx/tools/image-fx",
    max_wait_sec: float = 15.0,
    force_restart: bool = False,
) -> bool:
    """Ensure Google Chrome Remote Debugging (port 9222) is running. Auto-starts if offline."""
    base_url = f"http://127.0.0.1:{port}"
    if not force_restart and probe_flow_cdp_health(base_url):
        return True

    chrome_exe = find_chrome_executable()
    if not chrome_exe:
        raise FileNotFoundError("Google Chrome executable (chrome.exe) not found on system.")

    profile_env = os.environ.get("CHROME_FLOW_PROFILE")
    if profile_env:
        profile_dir = Path(profile_env)
    elif (Path.home() / ".chrome_debug_ep02").exists():
        profile_dir = Path.home() / ".chrome_debug_ep02"
    else:
        profile_dir = Path.home() / ".chrome_flow_profile"
    profile_dir.mkdir(parents=True, exist_ok=True)


    SCRATCH_LOG_DIR.mkdir(parents=True, exist_ok=True)
    log_file = SCRATCH_LOG_DIR / "chrome_cdp.log"

    print(f"[*] Auto-launching Google Chrome on port {port} with URL {target_url}...")
    if sys.platform == "win32":
        ps_cmd = (
            f"Start-Process -FilePath '{chrome_exe}' "
            f"-ArgumentList '--remote-debugging-port={port}', '--user-data-dir={profile_dir}', '--no-first-run', '--no-default-browser-check', '{target_url}' "
            f"-WindowStyle Hidden"
        )
        subprocess.run(["powershell", "-NoProfile", "-Command", ps_cmd], check=False)
    else:
        with open(log_file, "a", encoding="utf-8") as out_f:
            subprocess.Popen(
                [str(chrome_exe), f"--remote-debugging-port={port}", f"--user-data-dir={profile_dir}", target_url],
                stdout=out_f,
                stderr=subprocess.STDOUT,
                close_fds=True,
            )

    # Poll until Chrome responds to /json/version
    start_time = time.time()
    while time.time() - start_time < max_wait_sec:
        if probe_flow_cdp_health(base_url, timeout=1.0):
            print(f"[+] Google Chrome CDP is ONLINE at {base_url}")
            return True
        time.sleep(0.5)

    raise TimeoutError(
        f"Google Chrome failed to open CDP port {port} within {max_wait_sec}s. "
        f"Check log file at {log_file}."
    )


def ensure_external_services(
    require_tts: bool = False,
    require_flow: bool = False,
    auto_start: bool = True,
) -> Dict[str, bool]:
    """Preflight check that auto-launches offline services if auto_start=True."""
    status = {
        "supertonic3_tts": probe_supertonic3_health(),
        "google_flow_cdp": probe_flow_cdp_health(),
    }

    if require_tts:
        if not status["supertonic3_tts"]:
            if auto_start:
                ensure_supertonic3_running()
                status["supertonic3_tts"] = probe_supertonic3_health()
            else:
                raise ConnectionError("SuperTonic3 TTS is offline and auto_start is disabled.")

    if require_flow:
        if not status["google_flow_cdp"]:
            if auto_start:
                ensure_flow_cdp_chrome_running()
                status["google_flow_cdp"] = probe_flow_cdp_health()
            else:
                raise ConnectionError("Google Flow CDP is offline and auto_start is disabled.")

    return status


if __name__ == "__main__":
    print("External Service Manager Diagnostic:")
    print(f"  SuperTonic3 Root: {find_supertonic3_root()}")
    print(f"  Chrome Path:      {find_chrome_executable()}")
    print(f"  SuperTonic3 Status: {'ONLINE' if probe_supertonic3_health() else 'OFFLINE'}")
    print(f"  Flow CDP Status:    {'ONLINE' if probe_flow_cdp_health() else 'OFFLINE'}")
