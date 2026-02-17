@echo off
REM Chirp-STT autostart wrapper - launched hidden by chirp-autostart.vbs
REM This file lives in the repo root so %%~dp0 always resolves to the project directory.
cd /d "%~dp0"
uv run python -m chirp.main
