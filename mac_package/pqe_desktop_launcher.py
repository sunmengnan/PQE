#!/usr/bin/env python3
"""Frozen macOS launcher for PQE Dashboard.

This file is used by PyInstaller. It starts the Streamlit app without requiring users to open Terminal.
"""

from __future__ import annotations

import os
import socket
import sys
import threading
import time
import webbrowser
from pathlib import Path


def resource_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(getattr(sys, "_MEIPASS", Path(sys.executable).parent))
    return Path(__file__).resolve().parent.parent


def find_free_port(start: int = 8501, end: int = 8599) -> int:
    for port in range(start, end + 1):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.settimeout(0.1)
            if sock.connect_ex(("127.0.0.1", port)) != 0:
                return port
    raise RuntimeError("No available local port found from 8501 to 8599.")


def open_browser_later(url: str) -> None:
    time.sleep(2.5)
    webbrowser.open(url)


def main() -> int:
    app_dir = resource_dir()
    script_path = app_dir / "pqe_phase1_ui.py"
    if not script_path.exists():
        raise FileNotFoundError(f"Cannot find Streamlit UI script: {script_path}")

    port = find_free_port()
    url = f"http://127.0.0.1:{port}"
    os.environ.setdefault("STREAMLIT_BROWSER_GATHER_USAGE_STATS", "false")
    os.environ.setdefault("STREAMLIT_SERVER_HEADLESS", "true")

    threading.Thread(target=open_browser_later, args=(url,), daemon=True).start()

    from streamlit.web import bootstrap

    flag_options = {
        "server.port": port,
        "server.headless": True,
        "browser.gatherUsageStats": False,
    }
    bootstrap.run(str(script_path), False, [], flag_options)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
