@echo off
cd /d %USERPROFILE%\chirp-stt
uv run python -m chirp.main %*
