"""Entry point per il backend impacchettato (PyInstaller / Windows).

A differenza di `uvicorn main:app` (che usa una import-string e non funziona bene
in un eseguibile congelato), qui passiamo l'oggetto `app` direttamente a uvicorn.
La porta è configurabile via env DROPS_PORT (default 8000).
"""
import os

import uvicorn

from main import app

if __name__ == "__main__":
    host = os.environ.get("DROPS_HOST", "127.0.0.1")
    port = int(os.environ.get("DROPS_PORT", "8000"))
    uvicorn.run(app, host=host, port=port, log_level="info")
