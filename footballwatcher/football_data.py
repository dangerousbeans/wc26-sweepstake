"""football-data.org API client and the Match model used across the app."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone

import requests

BASE_URL = "https://api.football-data.org/v4"

# Statuses that mean the match has not started yet.
UPCOMING_STATUSES = {"SCHEDULED", "TIMED"}
FINISHED_STATUS = "FINISHED"


@dataclass
class Scorer:
    name: str
    team: str | None
    minute: int | None


@dataclass
class Match:
    id: int
    utc_kickoff: datetime
    status: str
    home_id: int | None
    away_id: int | None
    home_name: str
    away_name: str
    home_score: int | None
    away_score: int | None
    stage: str | None
    group: str | None
    scorers: list[Scorer] = field(default_factory=list)
    # Filled in by the alert engine: person(s) who own each side.
    home_owners: list[str] = field(default_factory=list)
    away_owners: list[str] = field(default_factory=list)

    @property
    def is_upcoming(self) -> bool:
        return self.status in UPCOMING_STATUSES

    @property
    def is_finished(self) -> bool:
        return self.status == FINISHED_STATUS

    @property
    def all_owners(self) -> list[str]:
        seen: dict[str, None] = {}
        for o in (*self.home_owners, *self.away_owners):
            seen.setdefault(o, None)
        return list(seen.keys())

    @classmethod
    def from_api(cls, data: dict) -> "Match":
        score = data.get("score", {}) or {}
        full_time = score.get("fullTime", {}) or {}
        home_team = data.get("homeTeam", {}) or {}
        away_team = data.get("awayTeam", {}) or {}

        scorers = []
        for goal in data.get("goals", []) or []:
            scorer = goal.get("scorer", {}) or {}
            team = goal.get("team", {}) or {}
            scorers.append(
                Scorer(
                    name=scorer.get("name", "Unknown"),
                    team=team.get("name"),
                    minute=goal.get("minute"),
                )
            )

        return cls(
            id=int(data["id"]),
            utc_kickoff=_parse_dt(data.get("utcDate")),
            status=data.get("status", "SCHEDULED"),
            home_id=_maybe_int(home_team.get("id")),
            away_id=_maybe_int(away_team.get("id")),
            home_name=home_team.get("name") or "TBD",
            away_name=away_team.get("name") or "TBD",
            home_score=full_time.get("home"),
            away_score=full_time.get("away"),
            stage=data.get("stage"),
            group=data.get("group"),
            scorers=scorers,
        )


def _maybe_int(value) -> int | None:
    return int(value) if value is not None else None


# Far-future sentinel for a missing kickoff. Deliberately NOT datetime.max:
# converting datetime.max to a positive-offset timezone (e.g. Europe/Amsterdam)
# overflows and raises. This sorts unknown-kickoff matches last and survives
# astimezone() in any timezone.
NO_KICKOFF = datetime(9999, 1, 1, tzinfo=timezone.utc)


def _parse_dt(value: str | None) -> datetime:
    if not value:
        return NO_KICKOFF
    # API uses e.g. "2026-06-14T19:00:00Z"
    dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
    # Guard against an ISO value with no zone — keep everything tz-aware so
    # comparisons against an aware `now` never raise.
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


class FootballDataClient:
    def __init__(self, token: str, base_url: str = BASE_URL, timeout: int = 20):
        self._token = token
        self._base_url = base_url
        self._timeout = timeout

    def _get(self, path: str, params: dict | None = None) -> dict:
        resp = requests.get(
            f"{self._base_url}{path}",
            headers={"X-Auth-Token": self._token},
            params=params,
            timeout=self._timeout,
        )
        resp.raise_for_status()
        return resp.json()

    def list_teams(self, competition_code: str) -> list[dict]:
        data = self._get(f"/competitions/{competition_code}/teams")
        return data.get("teams", [])

    def list_matches(self, competition_code: str) -> list[Match]:
        data = self._get(f"/competitions/{competition_code}/matches")
        matches: list[Match] = []
        for raw in data.get("matches", []):
            try:
                matches.append(Match.from_api(raw))
            except (KeyError, ValueError, TypeError) as exc:
                # One malformed record shouldn't sink the whole run.
                logging.getLogger("footballwatcher").warning(
                    "Skipping unparseable match %r: %s", raw.get("id"), exc
                )
        return matches
