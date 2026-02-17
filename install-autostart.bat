@echo off
REM Installs Chirp-STT to run silently at Windows login.
REM Creates a VBScript in the Startup folder that launches autostart.bat hidden.
REM Safe to run multiple times - overwrites any previous version.

setlocal enabledelayedexpansion

set "BAT=%~dp0autostart.bat"

REM Verify autostart.bat exists next to this script
if not exist "%BAT%" (
    echo ERROR: autostart.bat not found next to this script.
    echo        Make sure you run this from the chirp-stt repo root.
    pause
    exit /b 1
)

set "STARTUP=%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup"
set "VBS=%STARTUP%\chirp-autostart.vbs"

REM Write the VBScript (two lines) that launches autostart.bat with a hidden window
(
    echo Set WshShell = CreateObject^("WScript.Shell"^)
    echo WshShell.Run Chr^(34^) ^& "!BAT!" ^& Chr^(34^), 0, False
) > "%VBS%"

if exist "%VBS%" (
    echo Chirp-STT autostart installed.
    echo.
    echo   VBScript : %VBS%
    echo   Launches : %BAT%
    echo.
    echo Starting Chirp...
    wscript "%VBS%"
    echo Chirp is now running in the background.
) else (
    echo ERROR: Failed to create VBScript in Startup folder.
    pause
)
