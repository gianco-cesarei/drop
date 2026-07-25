# -*- mode: python ; coding: utf-8 -*-
"""Spec PyInstaller per Drops backend.

Produce un unico eseguibile `drops-backend.exe` (modalità onefile) che contiene
FastAPI + uvicorn + yt-dlp e tutti i moduli locali (main.py, spotify_agent.py).

Build:  pyinstaller --clean --noconfirm backend/drops-backend.spec
Output: dist/drops-backend.exe
"""
import os

from PyInstaller.utils.hooks import collect_all, collect_submodules

# SPECPATH è la cartella che contiene questo .spec (cioè backend/)
BACKEND_DIR = SPECPATH  # noqa: F821 (fornito da PyInstaller)

datas = []
binaries = []
hiddenimports = []

# Impacchetta il frontend (index.html) dentro l'exe: a runtime viene estratto
# in _MEIPASS/frontend/index.html e servito da serve_frontend().
_frontend = os.path.join(BACKEND_DIR, "..", "frontend", "index.html")
if not os.path.isfile(_frontend):
    raise SystemExit(
        f"[drops-backend.spec] frontend/index.html non trovato in {_frontend!r}: "
        "impossibile impacchettare la UI. Interrompo la build."
    )
datas += [(_frontend, "frontend")]

# Raccogli tutto (moduli, dati, binari) dai pacchetti che caricano risorse a runtime
for pkg in ("uvicorn", "yt_dlp", "fastapi", "pydantic", "anyio", "starlette"):
    _d, _b, _h = collect_all(pkg)
    datas += _d
    binaries += _b
    hiddenimports += _h

# uvicorn importa loop/protocolli in modo dinamico
hiddenimports += collect_submodules("uvicorn")

a = Analysis(
    [os.path.join(BACKEND_DIR, "run_backend.py")],
    pathex=[BACKEND_DIR],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name="drops-backend",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,          # niente finestra console: i log vanno in ~/.drops/logs
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
