"""Configuration loading from environment variables (and an optional .env file)."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent


def _load_dotenv(path: Path) -> None:
    """Minimal .env loader so we don't add a python-dotenv dependency.

    Only sets keys that are not already present in the environment.
    """
    if not path.exists():
        return
    for raw in path.read_text().splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        os.environ.setdefault(key, value)


@dataclass(frozen=True)
class Config:
    football_data_token: str
    anthropic_api_key: str
    summary_model: str
    smtp_host: str
    smtp_port: int
    smtp_user: str
    smtp_password: str
    email_from: str
    email_to: str
    timezone: str
    morning_digest_hour: int
    prematch_lead_minutes: int
    competition_code: str
    state_db: Path
    teams_file: Path
    dashboard_file: Path

    @classmethod
    def from_env(cls, *, load_dotenv: bool = True) -> "Config":
        if load_dotenv:
            _load_dotenv(PROJECT_ROOT / ".env")

        def _path(env_key: str, default: str) -> Path:
            value = os.environ.get(env_key, default)
            p = Path(value)
            return p if p.is_absolute() else PROJECT_ROOT / p

        return cls(
            football_data_token=os.environ.get("FOOTBALL_DATA_TOKEN", ""),
            anthropic_api_key=os.environ.get("ANTHROPIC_API_KEY", ""),
            summary_model=os.environ.get("SUMMARY_MODEL", "claude-opus-4-8"),
            smtp_host=os.environ.get("SMTP_HOST", "smtp.gmail.com"),
            smtp_port=int(os.environ.get("SMTP_PORT", "587")),
            smtp_user=os.environ.get("SMTP_USER", ""),
            smtp_password=os.environ.get("SMTP_PASSWORD", ""),
            email_from=os.environ.get("EMAIL_FROM", os.environ.get("SMTP_USER", "")),
            email_to=os.environ.get("EMAIL_TO", ""),
            timezone=os.environ.get("TIMEZONE", "Europe/Amsterdam"),
            morning_digest_hour=int(os.environ.get("MORNING_DIGEST_HOUR", "8")),
            prematch_lead_minutes=int(os.environ.get("PREMATCH_LEAD_MINUTES", "60")),
            competition_code=os.environ.get("COMPETITION_CODE", "WC"),
            state_db=_path("STATE_DB", "state.db"),
            teams_file=_path("TEAMS_FILE", "teams.json"),
            dashboard_file=_path("DASHBOARD_FILE", "dashboard.html"),
        )

    def require_for_run(self) -> None:
        """Raise a clear error if secrets needed for a live run are missing."""
        missing = [
            name
            for name, value in {
                "FOOTBALL_DATA_TOKEN": self.football_data_token,
                "ANTHROPIC_API_KEY": self.anthropic_api_key,
                "SMTP_USER": self.smtp_user,
                "SMTP_PASSWORD": self.smtp_password,
                "EMAIL_TO": self.email_to,
            }.items()
            if not value
        ]
        if missing:
            raise RuntimeError(
                "Missing required configuration: "
                + ", ".join(missing)
                + ". Copy .env.example to .env and fill these in."
            )
