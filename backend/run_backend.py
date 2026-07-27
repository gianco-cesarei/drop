"""Entry point per il backend impacchettato (PyInstaller / Windows).

A differenza di `uvicorn main:app` (che usa una import-string e non funziona bene
in un eseguibile congelato), qui passiamo l'oggetto `app` direttamente a uvicorn.
La porta è configurabile via env DROPS_PORT (default 8000).
"""
import os
import sys
import threading
import time

# ─── Fix PyInstaller "windowed" (console=False) su Windows ────────────────────
# In modalità windowed sys.stdout/sys.stderr sono None: uvicorn e il modulo
# logging scrivono su stderr all'avvio e andrebbero in crash PRIMA di aprire la
# porta → l'app non risponderebbe (finestra bianca). Redirigiamo gli stream
# mancanti su un file di log (fallback: devnull). Va fatto prima di importare
# uvicorn e configurare il logging.
if sys.stdout is None or sys.stderr is None:
    try:
        _log_dir = os.path.join(
            os.environ.get(
                "DROPS_STATE_DIR", os.path.join(os.path.expanduser("~"), ".drops")
            ),
            "logs",
        )
        os.makedirs(_log_dir, exist_ok=True)
        _stream = open(
            os.path.join(_log_dir, "uvicorn.log"), "a", buffering=1, encoding="utf-8"
        )
    except Exception:
        _stream = open(os.devnull, "w")
    if sys.stdout is None:
        sys.stdout = _stream
    if sys.stderr is None:
        sys.stderr = _stream

import uvicorn  # noqa: E402  (dopo il fix degli stream)

from main import app  # noqa: E402


def _watch_parent() -> None:
    """Termina backend se processo desktop padre non esiste più."""
    raw_pid = os.environ.get("DROPS_PARENT_PID")
    if not raw_pid:
        return
    try:
        parent_pid = int(raw_pid)
    except ValueError:
        return

    def monitor() -> None:
        while True:
            time.sleep(2)
            try:
                os.kill(parent_pid, 0)
            except (OSError, ProcessLookupError):
                os._exit(0)

    threading.Thread(target=monitor, name="drops-parent-watchdog", daemon=True).start()


if __name__ == "__main__":
    _watch_parent()
    host = os.environ.get("DROPS_HOST", "127.0.0.1")
    port = int(os.environ.get("DROPS_PORT", "8000"))
    uvicorn.run(app, host=host, port=port, log_level="info")
