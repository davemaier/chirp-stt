from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, Optional

from platformdirs import PlatformDirs


@dataclass(kw_only=True, slots=True)
class ChirpConfig:
    primary_shortcut: str = "win+alt+d"
    stt_backend: str = "parakeet"
    parakeet_model: str = "nemo-parakeet-tdt-0.6b-v3"
    parakeet_quantization: Optional[str] = None
    onnx_providers: str = "cpu"
    threads: Optional[int] = None
    language: Optional[str] = None
    word_overrides: Dict[str, str] = field(default_factory=dict)
    whisper_prompt: str = ""
    paste_mode: str = "ctrl"
    clipboard_behavior: bool = True
    clipboard_clear_delay: float = 0.75
    audio_feedback: bool = True
    start_sound_path: Optional[str] = None
    stop_sound_path: Optional[str] = None

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ChirpConfig":
        merged = DEFAULT_CONFIG | data
        merged["word_overrides"] = {
            str(k).lower(): str(v) for k, v in merged.get("word_overrides", {}).items()
        }
        merged["primary_shortcut"] = str(merged["primary_shortcut"]).lower()
        merged["paste_mode"] = str(merged["paste_mode"]).lower()
        merged["onnx_providers"] = str(merged["onnx_providers"]).lower()
        quant = merged.get("parakeet_quantization")
        merged["parakeet_quantization"] = str(quant).lower() if quant else None
        lang = merged.get("language")
        merged["language"] = str(lang) if lang else None
        return cls(**merged)

    def to_dict(self) -> Dict[str, Any]:
        payload = asdict(self)
        payload["word_overrides"] = dict(self.word_overrides)
        return payload


DEFAULT_CONFIG: Dict[str, Any] = {
    "primary_shortcut": "win+alt+d",
    "stt_backend": "parakeet",
    "parakeet_model": "nemo-parakeet-tdt-0.6b-v3",
    "parakeet_quantization": None,
    "onnx_providers": "cpu",
    "threads": None,
    "language": None,
    "word_overrides": {},
    "whisper_prompt": "",
    "paste_mode": "ctrl",
    "clipboard_behavior": True,
    "clipboard_clear_delay": 0.75,
    "audio_feedback": True,
    "start_sound_path": None,
    "stop_sound_path": None,
}


class ConfigManager:
    def __init__(self, *, app_name: str = "Chirp", app_author: str = "Will") -> None:
        dirs = PlatformDirs(app_name=app_name, appauthor=app_author, roaming=True)
        self._config_dir = Path(dirs.user_config_dir)
        self._config_path = self._config_dir / "config.json"

    @property
    def config_path(self) -> Path:
        return self._config_path

    def ensure_exists(self) -> None:
        if self._config_path.exists():
            return
        self._config_dir.mkdir(parents=True, exist_ok=True)
        self._config_path.write_text(json.dumps(DEFAULT_CONFIG, indent=2), encoding="utf-8")

    def load(self) -> ChirpConfig:
        self.ensure_exists()
        data = json.loads(self._config_path.read_text(encoding="utf-8"))
        return ChirpConfig.from_dict(data)

    def save(self, config: ChirpConfig) -> None:
        self._config_dir.mkdir(parents=True, exist_ok=True)
        self._config_path.write_text(json.dumps(config.to_dict(), indent=2), encoding="utf-8")
