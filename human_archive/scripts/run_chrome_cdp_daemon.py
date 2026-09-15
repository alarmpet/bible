# -*- coding: utf-8 -*-
"""
run_chrome_cdp_daemon.py
Background daemon supervisor that keeps Google Chrome running on port 9222
for Google Flow CDP automation.
"""

from __future__ import annotations

import os
import subprocess
import sys
import time
import urllib.request
import urllib.error
from pathlib import Path

CHROME_EXE = Path(r"C:\Program Files\Google\Chrome\Application\chrome.exe")
PROFILE_DIR = (
    Path(os.environ.get("CHROME_FLOW_PROFILE"))
    if os.environ.get("CHROME_FLOW_PROFILE")
    else (
        Path(r"C:\Users\shs\.chrome_debug_ep02")
        if Path(r"C:\Users\shs\.chrome_debug_ep02").exists()
        else Path(r"C:\Users\shs\.chrome_flow_profile")
    )
)
TARGET_URL = "https://labs.google/fx/tools/image-fx"
CDP_PORT = 9222



def is_cdp_alive() -> bool:
    try:
        with urllib.request.urlopen(f"http://127.0.0.1:{CDP_PORT}/json/version", timeout=1.0) as resp:
            return resp.status == 200
    except Exception:
        return False


def main():
    if not CHROME_EXE.exists():
        print(f"Error: Chrome executable missing at {CHROME_EXE}", file=sys.stderr)
        sys.exit(1)

    PROFILE_DIR.mkdir(parents=True, exist_ok=True)

    cmd = [
        str(CHROME_EXE),
        f"--remote-debugging-port={CDP_PORT}",
        f"--user-data-dir={PROFILE_DIR}",
        "--no-first-run",
        "--no-default-browser-check",
        TARGET_URL,
    ]

    print(f"Starting Chrome CDP Supervisor on port {CDP_PORT}...")
    log_path = Path(r"D:\module\scratch\service_logs\chrome_cdp_daemon.log")
    log_path.parent.mkdir(parents=True, exist_ok=True)

    with open(log_path, "a", encoding="utf-8") as log_f:
        log_f.write(f"\n--- Chrome CDP Daemon started at {time.strftime('%Y-%m-%d %H:%M:%S')} ---\n")
        proc = subprocess.Popen(cmd, stdout=log_f, stderr=subprocess.STDOUT)
        print(f"Chrome launched with PID {proc.pid}. Monitoring CDP port {CDP_PORT}...")

        # Wait for CDP to become active
        for _ in range(20):
            if is_cdp_alive():
                print(f"[ONLINE] Google Chrome CDP is alive and listening on http://127.0.0.1:{CDP_PORT}")
                break
            time.sleep(0.5)

        try:
            # Supervise process
            while True:
                ret = proc.poll()
                if ret is not None:
                    print(f"Chrome process exited with code {ret}. Restarting...")
                    proc = subprocess.Popen(cmd, stdout=log_f, stderr=subprocess.STDOUT)
                time.sleep(2.0)
        except KeyboardInterrupt:
            print("Stopping Chrome supervisor...")
            proc.terminate()


if __name__ == "__main__":
    main()
