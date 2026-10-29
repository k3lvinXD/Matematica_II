"""Procesos acotados para cálculo, gráficas y explicación opcional."""
import json
import os
from pathlib import Path
import subprocess
import sys
import threading
import logging

ROOT = Path(__file__).resolve().parent.parent
SLOTS = threading.BoundedSemaphore(2)


def run_worker(data, action="calculate", timeout=12):
    flags = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
    result = subprocess.run(
        [sys.executable, "-B", "-m", "modules.chat_worker" if action == "chat" else "modules.worker"],
        input=json.dumps({"action": action, "data": data}),
        capture_output=True, text=True, encoding="utf-8", cwd=ROOT,
        timeout=timeout, creationflags=flags, check=True)
    if action == "chat" and result.stderr:
        # Only our bounded diagnostic markers; never forward arbitrary stderr.
        for line in result.stderr.splitlines():
            if line.startswith(("gemini_http status=", "gemini_connection type=")):
                logging.getLogger(__name__).warning("%s", line[:100])
    return json.loads(result.stdout)
