"""Настройки приложения. Читаются из переменных окружения один раз при старте."""

import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Settings:
    db_path: Path = Path("data/timetracker.db")
    log_level: str = "INFO"

    @classmethod
    def from_env(cls) -> "Settings":
        return cls(
            db_path=Path(os.environ.get("TIMETRACKER_DB", str(cls.db_path))),
            log_level=os.environ.get("TIMETRACKER_LOG_LEVEL", cls.log_level).upper(),
        )
