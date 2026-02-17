@echo off
REM Removes Chirp-STT from Windows autostart.
del "%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup\chirp-autostart.vbs" 2>nul && (
    echo Chirp-STT autostart removed.
) || (
    echo Chirp-STT autostart was not installed - nothing to remove.
)
pause
