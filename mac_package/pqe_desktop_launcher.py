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
from urllib.error import URLError
from urllib.request import urlopen


LOG_DIR = Path.home() / "Library" / "Logs" / "PQE Dashboard"
LOG_FILE = LOG_DIR / "launcher.log"


def log(message: str) -> None:
    try:
        LOG_DIR.mkdir(parents=True, exist_ok=True)
        with LOG_FILE.open("a", encoding="utf-8") as handle:
            handle.write(time.strftime("%Y-%m-%d %H:%M:%S") + " " + message + "\n")
    except Exception:
        pass


def resource_dir() -> Path:
    if getattr(sys, "frozen", False):
        candidates = [
            Path(getattr(sys, "_MEIPASS", "")),
            Path(sys.executable).resolve().parents[1] / "Resources",
            Path(sys.executable).resolve().parent,
        ]
        for candidate in candidates:
            if candidate and (candidate / "pqe_phase1_ui.py").exists():
                return candidate
    return Path(__file__).resolve().parent.parent


def find_free_port(start: int = 8501, end: int = 8599) -> int:
    for port in range(start, end + 1):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.settimeout(0.1)
            if sock.connect_ex(("127.0.0.1", port)) != 0:
                return port
    raise RuntimeError("No available local port found from 8501 to 8599.")


def wait_for_server(url: str, timeout_seconds: int = 90) -> bool:
    deadline = time.time() + timeout_seconds
    while time.time() < deadline:
        try:
            with urlopen(url, timeout=2) as response:
                if response.status < 500:
                    return True
        except (OSError, URLError):
            time.sleep(0.5)
    return False


def open_browser_when_ready(url: str) -> None:
    if wait_for_server(url):
        log(f"Opening browser: {url}")
        webbrowser.open(url)
    else:
        log(f"Server did not become ready: {url}")


def main() -> int:
    log("Starting PQE Dashboard launcher")
    app_dir = resource_dir()
    log(f"Resource directory: {app_dir}")
    os.chdir(app_dir)
    if str(app_dir) not in sys.path:
        sys.path.insert(0, str(app_dir))
    script_path = app_dir / "pqe_phase1_ui.py"
    if not script_path.exists():
        log(f"Cannot find Streamlit UI script: {script_path}")
        raise FileNotFoundError(f"Cannot find Streamlit UI script: {script_path}")

    if os.environ.get("PQE_DASHBOARD_SMOKE_TEST") == "1":
        import pqe_phase1_mvp  # noqa: F401
        import pqe_phase1_ui  # noqa: F401
        log("Smoke test import completed")
        return 0

    port = find_free_port()
    url = f"http://127.0.0.1:{port}"
    log(f"Selected URL: {url}")
    os.environ.setdefault("STREAMLIT_BROWSER_GATHER_USAGE_STATS", "false")
    os.environ.setdefault("STREAMLIT_SERVER_HEADLESS", "true")
    os.environ.setdefault("STREAMLIT_SERVER_ENABLE_CORS", "false")
    os.environ.setdefault("STREAMLIT_SERVER_ENABLE_XSRF_PROTECTION", "false")

    threading.Thread(target=open_browser_when_ready, args=(url,), daemon=True).start()

    from streamlit.web import bootstrap

    flag_options = {
        "server.port": port,
        "server.headless": True,
        "server.enableCORS": False,
        "server.enableXsrfProtection": False,
        "browser.gatherUsageStats": False,
    }
    log("Starting Streamlit bootstrap")
    bootstrap.run(str(script_path), False, [], flag_options)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        log(f"Fatal error: {type(exc).__name__}: {exc}")
        raise
