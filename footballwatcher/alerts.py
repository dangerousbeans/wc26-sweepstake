"""The 'what's due right now' brain. Pure logic over matches + state + clock.

Kept free of I/O so it can be unit-tested exhaustively. The orchestrator in
main.py feeds it matches (already filtered to tracked teams with owners
attached), a state object for dedup, and the current time.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Protocol
from zoneinfo import ZoneInfo

from .football_data import Match


class StateView(Protocol):
    def prematch_sent(self, match_id: int) -> bool: ...
    def result_sent(self, match_id: int) -> bool: ...
    def digest_sent(self, digest_date: str) -> bool: ...


@dataclass
class AlertPlan:
    digest_date: str | None = None
    digest_matches: list[Match] = field(default_factory=list)
    prematch: list[Match] = field(default_factory=list)
    results: list[Match] = field(default_factory=list)

    @property
    def is_empty(self) -> bool:
        return not (self.digest_date or self.prematch or self.results)


def matches_on_local_date(matches: list[Match], local_date, tz: ZoneInfo) -> list[Match]:
    return [m for m in matches if m.utc_kickoff.astimezone(tz).date() == local_date]


def determine_due(
    matches: list[Match],
    state: StateView,
    now: datetime,
    *,
    timezone: str,
    morning_digest_hour: int,
    prematch_lead_minutes: int,
) -> AlertPlan:
    """Decide which alerts are due. `matches` should already be tracked-only.

    `now` must be timezone-aware (UTC). Returns a plan; the caller is
    responsible for sending and recording (so a send failure can be retried).
    """
    tz = ZoneInfo(timezone)
    local_now = now.astimezone(tz)
    plan = AlertPlan()

    matches = sorted(matches, key=lambda m: m.utc_kickoff)

    # --- morning digest: once per local day, at/after the configured hour,
    #     only when there are tracked matches that day. ---
    local_date = local_now.date()
    local_date_str = local_date.isoformat()
    if local_now.hour >= morning_digest_hour and not state.digest_sent(local_date_str):
        todays = matches_on_local_date(matches, local_date, tz)
        if todays:
            plan.digest_date = local_date_str
            plan.digest_matches = todays

    # --- pre-match nudge: kickoff within the lead window, once per match. ---
    # Only the upper bound is enforced: `is_upcoming` (status SCHEDULED/TIMED)
    # already excludes started/finished matches, so we don't need a `now <=
    # kickoff` lower bound. Omitting it means a missed cron tick — or a lead
    # shorter than the cron interval — still nudges instead of silently
    # skipping. Dedup (prematch_sent) ensures one nudge per match.
    lead = timedelta(minutes=prematch_lead_minutes)
    for m in matches:
        if not m.is_upcoming:
            continue
        if m.utc_kickoff <= now + lead and not state.prematch_sent(m.id):
            plan.prematch.append(m)

    # --- results: each finished match once. ---
    for m in matches:
        if m.is_finished and not state.result_sent(m.id):
            plan.results.append(m)

    return plan


def attach_owners(matches: list[Match], team_owners: dict[int, list[str]]) -> list[Match]:
    """Set home_owners/away_owners on each match from team-id -> owners."""
    for m in matches:
        m.home_owners = list(team_owners.get(m.home_id, [])) if m.home_id else []
        m.away_owners = list(team_owners.get(m.away_id, [])) if m.away_id else []
    return matches


def tracked_matches(matches: list[Match], tracked_team_ids: set[int]) -> list[Match]:
    """Matches involving at least one tracked team."""
    return [
        m
        for m in matches
        if (m.home_id in tracked_team_ids) or (m.away_id in tracked_team_ids)
    ]
