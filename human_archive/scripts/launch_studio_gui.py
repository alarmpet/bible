# -*- coding: utf-8 -*-
"""Desktop launcher for NOLLAM Documentary Production Studio GUI:
Starts FastAPI server on 127.0.0.1:8765 and opens the default browser."""
from __future__ import annotations

import subprocess
import sys
import time
import urllib.request
import webbrowser
from pathlib import Path

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

SERVER_SCRIPT = Path(__file__).resolve().parent / "studio_gui_server.py"
PORT = 8765
URL = f"http://127.0.0.1:{PORT}"


def wait_for_server(url: str, timeout: float = 10.0) -> bool:
    start_time = time.time()
    while time.time() - start_time < timeout:
        try:
            with urllib.request.urlopen(url, timeout=1.0) as resp:
                if resp.status == 200:
                    return True
        except Exception:
            time.sleep(0.3)
    return False


def main():
    print("=" * 70)
    print("🎬 NOLLAM Documentary Studio GUI Launcher")
    print(f"Target URL: {URL}")
    print("=" * 70)

    # Start FastAPI / Uvicorn server in a subprocess
    print("Starting background FastAPI server...")
    proc = subprocess.Popen([sys.executable, str(SERVER_SCRIPT)])

    try:
        print(f"Waiting for server to become responsive on port {PORT}...")
        if wait_for_server(URL, timeout=12.0):
            print(f"✅ Server is LIVE! Opening browser: {URL}")
            webbrowser.open(URL)
        else:
            print(f"⚠️ Server took longer than expected to respond. Please open {URL} manually.")

        print("\n[STUDIO GUI RUNNING] Press Ctrl+C in this terminal to shutdown.")
        proc.wait()
    except KeyboardInterrupt:
        print("\nShutting down Studio GUI server...")
        proc.terminate()
        proc.wait()
        print("Server shutdown complete.")


if __name__ == "__main__":
    main()
