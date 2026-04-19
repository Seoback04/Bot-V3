"""Runtime settings loaded from environment variables (with .env support)."""
from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv


load_dotenv(override=False)


def _as_bool(value: str | None, default: bool = False) -> bool:
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "y", "on"}


@dataclass(frozen=True)
class Settings:
    openai_api_key: str | None
    openai_model: str
    headless: bool
    allow_real_submit: bool
    log_level: str
    output_dir: Path
    project_root: Path

    @property
    def ai_enabled(self) -> bool:
        return bool(self.openai_api_key)


def load_settings() -> Settings:
    project_root = Path(__file__).resolve().parent.parent
    output_dir = Path(os.getenv("OUTPUT_DIR", "outputs"))
    if not output_dir.is_absolute():
        output_dir = project_root / output_dir
    output_dir.mkdir(parents=True, exist_ok=True)

    return Settings(
        openai_api_key=os.getenv("OPENAI_API_KEY") or None,
        openai_model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
        headless=_as_bool(os.getenv("HEADLESS"), default=False),
        allow_real_submit=_as_bool(os.getenv("ALLOW_REAL_SUBMIT"), default=False),
        log_level=os.getenv("LOG_LEVEL", "INFO").upper(),
        output_dir=output_dir,
        project_root=project_root,
    )


SETTINGS = load_settings()
