"""Shared test helpers: a fake state store and a Match factory."""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

from footballwatcher.football_data import Match, Scorer


class FakeState:
    """In-memory StateView for testing the alert engine."""

    def __init__(self):
        self.prematch: set[int] = set()
        self.results: set[int] = set()
        self.digests: set[str] = set()

    def prematch_sent(self, match_id: int) -> bool:
        return match_id in self.prematch

    def result_sent(self, match_id: int) -> bool:
        return match_id in self.results

    def digest_sent(self, digest_date: str) -> bool:
        return digest_date in self.digests


@pytest.fixture
def fake_state() -> FakeState:
    return FakeState()


def make_match(
    *,
    match_id: int = 1,
    kickoff: str = "2026-06-14T19:00:00+00:00",
    status: str = "TIMED",
    home_id: int = 100,
    away_id: int = 200,
    home_name: str = "Netherlands",
    away_name: str = "France",
    home_score: int | None = None,
    away_score: int | None = None,
    scorers: list[Scorer] | None = None,
    home_owners: list[str] | None = None,
    away_owners: list[str] | None = None,
) -> Match:
    return Match(
        id=match_id,
        utc_kickoff=datetime.fromisoformat(kickoff),
        status=status,
        home_id=home_id,
        away_id=away_id,
        home_name=home_name,
        away_name=away_name,
        home_score=home_score,
        away_score=away_score,
        stage="GROUP_STAGE",
        group="GROUP_A",
        scorers=scorers or [],
        home_owners=home_owners or [],
        away_owners=away_owners or [],
    )


@pytest.fixture
def match_factory():
    return make_match


def utc(s: str) -> datetime:
    return datetime.fromisoformat(s).replace(tzinfo=timezone.utc) if "+" not in s else datetime.fromisoformat(s)
