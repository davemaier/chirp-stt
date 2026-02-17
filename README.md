# Chirp-STT

Chirp is a Windows dictation app that runs fully locally using ParakeetV3 STT and is managed end-to-end with `uv`. No .exe files, no installers, no admin rights — if you can run Python, you can run Chirp.

## Prerequisites

Install [uv](https://docs.astral.sh/uv/) (Python package manager):
```powershell
winget install astral-sh.uv
```

## Setup

Run the following commands in **PowerShell** (not cmd).

```powershell
cd ~
git clone https://github.com/Whamp/chirp.git chirp-stt
cd chirp-stt
uv run python -m chirp.setup   # one-time model download
```

## Running

From the chirp-stt directory:
```powershell
uv run python -m chirp.main
```

Press the hotkey (default `Ctrl+Shift+Space`) to start/stop dictation. Transcribed text is typed into the active window.

## Autostart (optional)

Chirp can start silently (no console window) every time you log in to Windows.

- **Install:** double-click `install-autostart.bat` in the repo root.
- **Remove:** double-click `uninstall-autostart.bat`, or simply delete `chirp-autostart.vbs` from your Startup folder.

Since there is no visible window, use Task Manager or `taskkill /f /im python.exe` to stop Chirp.

## Customization

Edit `config.toml` in the repo root. It has sensible defaults but is fully customizable:

```toml
primary_shortcut = "ctrl+shift+space"             # Hotkey that toggles recording
parakeet_quantization = ""                      # Set to "int8" for the quantized model variant
onnx_providers = "cpu"                          # ONNX runtime provider (e.g. "cuda", "cpu|dml")
threads = 0                                     # 0 lets ONNX decide; set a positive integer to pin thread usage
language = "en"                                 # ISO language code; leave blank for auto-detect
post_processing = ""                            # Style guide prompt (e.g. "sentence case")
audio_feedback = true                           # Start/stop chime playback

# Word overrides map spoken tokens (case-insensitive) to replacement text.
[word_overrides]
parrakeat = "parakeet"
"parra keat" = "parakeet"
```

See `config.toml` for the full list of options.

## Removal

- Run `uninstall-autostart.bat` if you installed autostart.
- Delete the cloned `chirp-stt` directory.
- That's it.

---

## Why ParakeetV3?

ParakeetV3 has indistinguishable accuracy from Whisper-large-V3 (multilingual WER 4.91 vs 5.05) but is 17x faster and only requires a CPU while Whisper models of comparable accuracy require GPU's.

https://huggingface.co/spaces/hf-audio/open_asr_leaderboard

## Architecture

- `src/chirp/main.py` — CLI entrypoint and application loop.
- `src/chirp/config_manager.py` — configuration loading and Windows-specific paths.
- `src/chirp/parakeet_manager.py` — Parakeet backend integration and provider handling.
- `src/chirp/setup.py` — one-time setup routine that prepares local model assets.

## Acknowledgments

- NVIDIA - https://huggingface.co/nvidia/parakeet-tdt-0.6b-v3
- Ilya Stupakov - https://huggingface.co/istupakov/parakeet-tdt-0.6b-v3-onnx
