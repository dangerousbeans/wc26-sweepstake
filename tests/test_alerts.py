"""The 'what's due' dedup brain."""

from __future__ import annotations

from datetime import datetime, timezone

from footballwatcher import alerts

TZ = "Europe/Amsterdam"
# 2026-06-14 18:30 UTC == 20:30 local (CEST). Local date 2026-06-14, hour 20.
NOW = datetime(2026, 6, 14, 18, 30, tzinfo=timezone.utc)

KW = dict(timezone=TZ, morning_digest_hour=8, prematch_lead_minutes=60)


def test_prematch_due_within_window(match_factory, fake_state):
    m = match_factory(kickoff="2026-06-14T19:00:00+00:00", status="TIMED")
    plan = alerts.determine_due([m], fake_state, NOW, **KW)
    assert [x.id for x in plan.prematch] == [m.id]


def test_prematch_not_due_when_already_sent(match_factory, fake_state):
    m = match_factory(kickoff="2026-06-14T19:00:00+00:00", status="TIMED")
    fake_state.prematch.add(m.id)
    plan = alerts.determine_due([m], fake_state, NOW, **KW)
    assert plan.prematch == []


def test_prematch_not_due_too_far_out(match_factory, fake_state):
    m = match_factory(kickoff="2026-06-14T22:00:00+00:00", status="TIMED")
    plan = alerts.determine_due([m], fake_state, NOW, **KW)
    assert plan.prematch == []


def test_prematch_not_due_after_kickoff(match_factory, fake_state):
    m = match_factory(kickoff="2026-06-14T18:00:00+00:00", status="IN_PLAY")
    plan = alerts.determine_due([m], fake_state, NOW, **KW)
    assert plan.prematch == []


def test_result_due_when_finished(match_factory, fake_state):
    m = match_factory(
        kickoff="2026-06-14T15:00:00+00:00",
        status="FINISHED",
        home_score=2,
        away_score=1,
    )
    plan = alerts.determine_due([m], fake_state, NOW, **KW)
    assert [x.id for x in plan.results] == [m.id]


def test_result_not_due_when_already_sent(match_factory, fake_state):
    m = match_factory(status="FINISHED", home_score=0, away_score=0)
    fake_state.results.add(m.id)
    plan = alerts.determine_due([m], fake_state, NOW, **KW)
    assert plan.results == []


def test_result_not_due_when_not_finished(match_factory, fake_state):
    m = match_factory(status="IN_PLAY", home_score=1, away_score=0)
    plan = alerts.determine_due([m], fake_state, NOW, **KW)
    assert plan.results == []


def test_morning_digest_due_with_matches_today(match_factory, fake_state):
    m = match_factory(kickoff="2026-06-14T19:00:00+00:00", status="TIMED")
    plan = alerts.determine_due([m], fake_state, NOW, **KW)
    assert plan.digest_date == "2026-06-14"
    assert [x.id for x in plan.digest_matches] == [m.id]


def test_morning_digest_not_due_before_hour(match_factory, fake_state):
    m = match_factory(kickoff="2026-06-14T19:00:00+00:00", status="TIMED")
    early = datetime(2026, 6, 14, 4, 0, tzinfo=timezone.utc)  # 06:00 local, < 8
    plan = alerts.determine_due([m], fake_state, early, **KW)
    assert plan.digest_date is None


def test_morning_digest_not_resent(match_factory, fake_state):
    m = match_factory(kickoff="2026-06-14T19:00:00+00:00", status="TIMED")
    fake_state.digests.add("2026-06-14")
    plan = alerts.determine_due([m], fake_state, NOW, **KW)
    assert plan.digest_date is None


def test_morning_digest_skipped_when_no_matches_today(match_factory, fake_state):
    m = match_factory(kickoff="2026-06-20T19:00:00+00:00", status="TIMED")
    plan = alerts.determine_due([m], fake_state, NOW, **KW)
    assert plan.digest_date is None


def test_tracked_matches_filters_by_team_id(match_factory):
    tracked = match_factory(match_id=1, home_id=100, away_id=999)
    untracked = match_factory(match_id=2, home_id=500, away_id=600)
    result = alerts.tracked_matches([tracked, untracked], {100, 200})
    assert [m.id for m in result] == [1]


def test_attach_owners_labels_both_sides(match_factory):
    m = match_factory(home_id=100, away_id=200)
    alerts.attach_owners([m], {100: ["Joran"], 200: ["Anh"]})
    assert m.home_owners == ["Joran"]
    assert m.away_owners == ["Anh"]
    assert m.all_owners == ["Joran", "Anh"]


def test_empty_plan(fake_state):
    plan = alerts.determine_due([], fake_state, NOW, **KW)
    assert plan.is_empty
