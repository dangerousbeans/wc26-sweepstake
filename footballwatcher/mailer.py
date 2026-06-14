"""Render alert emails (Jinja2) and send them via Gmail SMTP."""

from __future__ import annotations

import hashlib
import smtplib
from dataclasses import dataclass
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path
from zoneinfo import ZoneInfo

from jinja2 import Environment, FileSystemLoader, select_autoescape

from .football_data import Match

TEMPLATES_DIR = Path(__file__).resolve().parent / "templates"


def _build_env(timezone: str) -> Environment:
    env = Environment(
        loader=FileSystemLoader(str(TEMPLATES_DIR)),
        autoescape=select_autoescape(["html"]),
    )
    tz = ZoneInfo(timezone)

    def local_time(dt) -> str:
        return dt.astimezone(tz).strftime("%a %d %b, %H:%M")

    def owners_label(match: Match) -> str:
        bits = []
        if match.home_owners:
            bits.append(f"{match.home_name} → {', '.join(match.home_owners)}")
        if match.away_owners:
            bits.append(f"{match.away_name} → {', '.join(match.away_owners)}")
        return " | ".join(bits)

    def person_color(name: str) -> str:
        """Deterministic neon HSL colour per person (stable across runs)."""
        h = int(hashlib.md5(name.encode("utf-8")).hexdigest(), 16)
        hue = h % 360
        return f"hsl({hue} 90% 60%)"

    env.filters["local_time"] = local_time
    env.filters["owners_label"] = owners_label
    env.filters["person_color"] = person_color
    return env


@dataclass
class RenderedEmail:
    subject: str
    html: str
    text: str


class Mailer:
    def __init__(
        self,
        *,
        host: str,
        port: int,
        user: str,
        password: str,
        email_from: str,
        email_to: str,
        timezone: str,
    ):
        self._host = host
        self._port = port
        self._user = user
        self._password = password
        self._from = email_from
        self._to = email_to
        self._env = _build_env(timezone)

    def render(self, template_base: str, subject: str, **context) -> RenderedEmail:
        html = self._env.get_template(f"{template_base}.html.j2").render(**context)
        text = self._env.get_template(f"{template_base}.txt.j2").render(**context)
        return RenderedEmail(subject=subject, html=html, text=text)

    def send(self, email: RenderedEmail) -> None:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = email.subject
        msg["From"] = self._from
        msg["To"] = self._to
        msg.attach(MIMEText(email.text, "plain", "utf-8"))
        msg.attach(MIMEText(email.html, "html", "utf-8"))

        with smtplib.SMTP(self._host, self._port, timeout=30) as server:
            server.starttls()
            server.login(self._user, self._password)
            server.sendmail(self._from, [self._to], msg.as_string())
