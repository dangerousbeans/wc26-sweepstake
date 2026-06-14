"""Leaderboard scoring."""

from __future__ import annotations

from footballwatcher.leaderboard import compute_leaderboard
from tests.conftest import make_match


def test_win_draw_loss_points():
    matches = [
        # Joran's Netherlands beat France 2-1 -> Joran +3
        make_match(match_id=1, status="FINISHED", home_score=2, away_score=1,
                   home_owners=["Joran"], away_owners=[]),
        # Rich's Brazil drew 1-1 -> Rich +1
        make_match(match_id=2, status="FINISHED", home_score=1, away_score=1,
                   home_owners=["Rich"], away_owners=[]),
        # Tam's Japan lost 0-3 (as away) -> Tam +0
        make_match(match_id=3, status="FINISHED", home_score=3, away_score=0,
                   home_owners=[], away_owners=["Tam"]),
    ]
    board = {s.person: s for s in compute_leaderboard(matches, ["Joran", "Rich", "Tam"])}
    assert board["Joran"].points == 3 and board["Joran"].won == 1
    assert board["Rich"].points == 1 and board["Rich"].drawn == 1
    assert board["Tam"].points == 0 and board["Tam"].lost == 1
    assert board["Tam"].goals_for == 0


def test_head_to_head_credits_both_sides():
    # Joran's Netherlands 2-1 Ash's France: winner +3, loser +0, both played.
    m = make_match(match_id=1, status="FINISHED", home_score=2, away_score=1,
                   home_owners=["Joran"], away_owners=["Ash"])
    board = {s.person: s for s in compute_leaderboard([m], ["Joran", "Ash"])}
    assert board["Joran"].points == 3
    assert board["Ash"].points == 0 and board["Ash"].played == 1


def test_unfinished_matches_ignored():
    m = make_match(status="IN_PLAY", home_score=1, away_score=0, home_owners=["Joran"])
    board = compute_leaderboard([m], ["Joran"])
    assert board[0].played == 0 and board[0].points == 0


def test_all_people_present_even_with_zero_played():
    board = compute_leaderboard([], ["Joran", "Rich", "Ash"])
    assert {s.person for s in board} == {"Joran", "Rich", "Ash"}
    assert all(s.played == 0 for s in board)


def test_sorted_by_points_then_goals():
    matches = [
        make_match(match_id=1, status="FINISHED", home_score=5, away_score=0,
                   home_owners=["A"]),                     # A: 3 pts, 5 GF
        make_match(match_id=2, status="FINISHED", home_score=1, away_score=0,
                   home_owners=["B"]),                     # B: 3 pts, 1 GF
        make_match(match_id=3, status="FINISHED", home_score=0, away_score=0,
                   home_owners=["C"]),                     # C: 1 pt
    ]
    order = [s.person for s in compute_leaderboard(matches, ["A", "B", "C"])]
    assert order == ["A", "B", "C"]  # A & B tied on points, A ahead on goals


def test_person_owning_multiple_teams_aggregates():
    matches = [
        make_match(match_id=1, status="FINISHED", home_score=1, away_score=0,
                   home_owners=["Joran"]),
        make_match(match_id=2, status="FINISHED", home_score=2, away_score=0,
                   home_owners=["Joran"]),
    ]
    board = compute_leaderboard(matches, ["Joran"])
    assert board[0].points == 6 and board[0].played == 2 and board[0].goals_for == 3
