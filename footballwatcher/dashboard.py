"""Generate a self-contained static dashboard.html of all tracked matches."""

from __future__ import annotations

import itertools
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from .football_data import Match
from .leaderboard import compute_leaderboard
from .mailer import _build_env


def _people_from_matches(matches: list[Match]) -> list[str]:
    seen: dict[str, None] = {}
    for m in matches:
        for o in (*m.home_owners, *m.away_owners):
            seen.setdefault(o, None)
    return list(seen.keys())


def render_dashboard(
    matches: list[Match],
    generated_at: datetime,
    *,
    timezone: str,
    people: list[str] | None = None,
    picks: list[tuple[str, list[str]]] | None = None,
) -> str:
    tz = ZoneInfo(timezone)
    ordered = sorted(matches, key=lambda m: m.utc_kickoff)

    def day_key(m: Match) -> str:
        return m.utc_kickoff.astimezone(tz).strftime("%A %d %B %Y")

    days = [
        (day, list(group))
        for day, group in itertools.groupby(ordered, key=day_key)
    ]

    standings = compute_leaderboard(matches, people or _people_from_matches(matches))

    env = _build_env(timezone)
    template = env.get_template("dashboard.html.j2")
    return template.render(
        days=days,
        total=len(ordered),
        generated_at=generated_at,
        standings=standings,
        picks=picks or [],
    )


def write_dashboard(
    path: Path,
    matches: list[Match],
    generated_at: datetime,
    *,
    timezone: str,
    people: list[str] | None = None,
    picks: list[tuple[str, list[str]]] | None = None,
) -> Path:
    html = render_dashboard(
        matches, generated_at, timezone=timezone, people=people, picks=picks
    )
    out = Path(path)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(html, encoding="utf-8")
    return out
