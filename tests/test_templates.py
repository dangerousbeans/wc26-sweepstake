"""Template + dashboard rendering, Match parsing, state store, summarizer fallback."""

from __future__ import annotations

from datetime import datetime, timezone

from footballwatcher.dashboard import render_dashboard
from footballwatcher.football_data import Match, Scorer
from footballwatcher.mailer import Mailer
from footballwatcher.state import StateStore
from footballwatcher.summarizer import fallback_summary

TZ = "Europe/Amsterdam"


def _mailer():
    return Mailer(
        host="h", port=587, user="u", password="p",
        email_from="f@x.com", email_to="t@x.com", timezone=TZ,
    )


def test_morning_digest_renders(match_factory):
    m = match_factory(home_owners=["Joran"], away_owners=["Anh"])
    email = _mailer().render(
        "morning_digest", subject="s", digest_date="2026-06-14", matches=[m]
    )
    assert "Netherlands vs France" in email.html
    assert "Netherlands vs France" in email.text
    assert "Joran" in email.html and "Anh" in email.html


def test_prematch_renders(match_factory):
    m = match_factory(home_owners=["Joran"])
    email = _mailer().render("prematch", subject="s", match=m)
    assert "Netherlands vs France" in email.html
    assert "Joran" in email.text


def test_result_renders_with_summary(match_factory):
    m = match_factory(
        status="FINISHED",
        home_score=2,
        away_score=1,
        scorers=[Scorer(name="Gakpo", team="Netherlands", minute=23)],
        home_owners=["Joran"],
    )
    email = _mailer().render(
        "result", subject="s", match=m, summary="A thrilling win."
    )
    assert "2" in email.html and "1" in email.html
    assert "A thrilling win." in email.html
    assert "Gakpo" in email.html
    assert "A thrilling win." in email.text


def test_dashboard_renders_and_groups_by_day(match_factory):
    day1 = match_factory(match_id=1, kickoff="2026-06-14T19:00:00+00:00")
    day2 = match_factory(
        match_id=2, kickoff="2026-06-15T16:00:00+00:00",
        status="FINISHED", home_score=1, away_score=0,
    )
    html = render_dashboard([day1, day2], datetime.now(timezone.utc), timezone=TZ)
    assert "World Cup Sweepstake" in html
    assert "Netherlands" in html and "France" in html
    assert "1–0" in html
    assert "FINISHED" in html


def test_dashboard_empty():
    html = render_dashboard([], datetime.now(timezone.utc), timezone=TZ)
    assert "No tracked matches found." in html


def test_dashboard_embeds_youtube():
    html = render_dashboard([], datetime.now(timezone.utc), timezone=TZ)
    assert "youtube.com/embed/SCgR8h8iRnw" in html


def test_no_sparkles_before_anyone_scores():
    # Empty board (everyone on 0) must not sparkle.
    html = render_dashboard([], datetime.now(timezone.utc), timezone=TZ)
    assert 'class="spark' not in html


def test_dashboard_has_leaderboard_and_pills_and_h2h(match_factory):
    h2h = match_factory(
        match_id=1, status="FINISHED", home_score=2, away_score=1,
        home_owners=["Joran"], away_owners=["Ash"],
    )
    solo = match_factory(
        match_id=2, kickoff="2026-06-15T16:00:00+00:00",
        home_owners=["Rich"], away_owners=[],
    )
    html = render_dashboard(
        [h2h, solo], datetime.now(timezone.utc), timezone=TZ,
        people=["Joran", "Ash", "Rich"],
    )
    assert "Leaderboard" in html
    assert "head-to-head" in html.lower()  # both-owned match flagged
    assert 'class="pill"' in html          # owner pills rendered
    # Joran won the h2h -> appears with 3 points somewhere in the board
    assert "Joran" in html and "Ash" in html and "Rich" in html
    assert 'class="spark' in html  # leader (Joran, 3pts) gets sparkles


def test_dashboard_picks_section(match_factory):
    m = match_factory(home_owners=["Joran"], away_owners=["Ash"])
    html = render_dashboard(
        [m], datetime.now(timezone.utc), timezone=TZ,
        people=["Joran", "Ash"],
        picks=[("Joran", ["Netherlands", "Croatia"]), ("Ash", ["France", "Spain"])],
    )
    assert "who has which team" in html.lower()
    assert "Croatia" in html and "Spain" in html
    assert 'class="team-chip"' in html


def test_match_from_api_parses_core_fields():
    data = {
        "id": 42,
        "utcDate": "2026-06-14T19:00:00Z",
        "status": "FINISHED",
        "stage": "GROUP_STAGE",
        "group": "GROUP_A",
        "homeTeam": {"id": 100, "name": "Netherlands"},
        "awayTeam": {"id": 200, "name": "France"},
        "score": {"fullTime": {"home": 2, "away": 1}},
        "goals": [
            {"scorer": {"name": "Gakpo"}, "team": {"name": "Netherlands"}, "minute": 23}
        ],
    }
    m = Match.from_api(data)
    assert m.id == 42
    assert m.is_finished
    assert m.home_id == 100 and m.away_id == 200
    assert m.home_score == 2 and m.away_score == 1
    assert m.utc_kickoff == datetime(2026, 6, 14, 19, 0, tzinfo=timezone.utc)
    assert m.scorers[0].name == "Gakpo" and m.scorers[0].minute == 23


def test_match_from_api_handles_missing_optional_fields():
    data = {
        "id": 1,
        "utcDate": "2026-06-14T19:00:00Z",
        "status": "TIMED",
        "homeTeam": {"id": 100, "name": "Netherlands"},
        "awayTeam": {},
        "score": {},
    }
    m = Match.from_api(data)
    assert m.away_id is None
    assert m.away_name == "TBD"
    assert m.home_score is None
    assert m.is_upcoming


def test_state_store_dedup(tmp_path):
    db = tmp_path / "state.db"
    with StateStore(db) as state:
        assert not state.prematch_sent(1)
        state.mark_prematch_sent(1)
        assert state.prematch_sent(1)

        assert not state.result_sent(1)
        state.mark_result_sent(1)
        assert state.result_sent(1)
        # prematch flag preserved through the result upsert
        assert state.prematch_sent(1)

        assert not state.digest_sent("2026-06-14")
        state.mark_digest_sent("2026-06-14")
        assert state.digest_sent("2026-06-14")

    # Persists across connections.
    with StateStore(db) as state:
        assert state.prematch_sent(1)
        assert state.result_sent(1)
        assert state.digest_sent("2026-06-14")


def test_missing_utcdate_survives_positive_offset_tz():
    """A match with no utcDate must not overflow astimezone() in a +offset tz."""
    m = Match.from_api(
        {
            "id": 9,
            "status": "SCHEDULED",
            "homeTeam": {"id": 100, "name": "Netherlands"},
            "awayTeam": {"id": 200, "name": "France"},
            "score": {},
        }
    )
    # Both the dashboard and the digest path call astimezone on this.
    html = render_dashboard([m], datetime.now(timezone.utc), timezone="Europe/Amsterdam")
    assert "Netherlands" in html and "France" in html


def test_list_matches_skips_malformed_record():
    """One bad match record must not sink the whole batch."""
    from unittest.mock import patch
    from footballwatcher.football_data import FootballDataClient

    client = FootballDataClient(token="x")
    payload = {
        "matches": [
            {"id": 1, "utcDate": "2026-06-14T19:00:00Z", "status": "TIMED",
             "homeTeam": {"id": 100, "name": "NL"}, "awayTeam": {"id": 200, "name": "FR"},
             "score": {}},
            {"status": "TIMED"},  # missing id -> should be skipped, not raise
        ]
    }
    with patch.object(client, "_get", return_value=payload):
        matches = client.list_matches("WC")
    assert [m.id for m in matches] == [1]


def test_avatars_load_as_data_uris():
    from footballwatcher.avatars import load_avatar_uris

    uris = load_avatar_uris()
    # The 8 sweepstake people have committed avatars.
    for person in ["Joran", "Barrett", "Alanah", "Rich", "Sylvia", "Tam", "Ash", "Jackie"]:
        assert person in uris, f"missing avatar for {person}"
        assert uris[person].startswith("data:image/png;base64,")


def test_dashboard_embeds_avatar_and_flag(match_factory):
    m = match_factory(home_name="Netherlands", home_owners=["Joran"])
    from footballwatcher.avatars import load_avatar_uris

    html = render_dashboard(
        [m], datetime.now(timezone.utc), timezone=TZ,
        people=["Joran"], picks=[("Joran", ["Netherlands"])],
    )
    # Avatar embedded as a data URI, flag emoji present for Netherlands.
    assert "data:image/png;base64," in html
    assert "\U0001F1F3\U0001F1F1" in html  # 🇳🇱


def test_fallback_summary(match_factory):
    m = match_factory(
        status="FINISHED", home_score=3, away_score=0,
        scorers=[Scorer(name="Kane", team="England", minute=12)],
    )
    text = fallback_summary(m)
    assert "Netherlands 3-0 France" in text
    assert "Kane" in text
