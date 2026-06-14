"""Compute a sweepstake leaderboard from finished matches.

Scoring (per person, summed across all teams they own):
  win  = 3 points
  draw = 1 point
  loss = 0 points
Ties broken by goals-for, then name. Goals-for is tracked for display and
tie-breaking only.
"""

from __future__ import annotations

from dataclasses import dataclass

from .football_data import Match

WIN_POINTS = 3
DRAW_POINTS = 1


@dataclass
class Standing:
    person: str
    points: int = 0
    won: int = 0
    drawn: int = 0
    lost: int = 0
    goals_for: int = 0
    played: int = 0

    def record(self, scored: int, conceded: int) -> None:
        self.played += 1
        self.goals_for += scored
        if scored > conceded:
            self.won += 1
            self.points += WIN_POINTS
        elif scored == conceded:
            self.drawn += 1
            self.points += DRAW_POINTS
        else:
            self.lost += 1


def compute_leaderboard(matches: list[Match], people: list[str]) -> list[Standing]:
    """Return standings for every person, sorted best-first.

    Every person in `people` appears, even with zero played, so the board is
    stable from the start of the tournament. A head-to-head match credits both
    sides' owners independently.
    """
    standings = {p: Standing(person=p) for p in people}

    for m in matches:
        if not m.is_finished or m.home_score is None or m.away_score is None:
            continue
        for owner in m.home_owners:
            standings.setdefault(owner, Standing(person=owner)).record(
                m.home_score, m.away_score
            )
        for owner in m.away_owners:
            standings.setdefault(owner, Standing(person=owner)).record(
                m.away_score, m.home_score
            )

    return sorted(
        standings.values(),
        key=lambda s: (-s.points, -s.goals_for, s.person),
    )
