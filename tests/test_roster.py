"""Roster loading and owner reverse-index."""

from __future__ import annotations

import textwrap

from footballwatcher.roster import Roster


def _write(tmp_path, text):
    p = tmp_path / "roster.yaml"
    p.write_text(textwrap.dedent(text))
    return p


def test_loads_entries_and_numbers(tmp_path):
    path = _write(
        tmp_path,
        """
        people:
          Joran:
            - { country: Netherlands, number: 8 }
            - { country: South Africa, number: null }
        """,
    )
    roster = Roster.load(path)
    assert len(roster.entries) == 2
    netherlands = next(e for e in roster.entries if e.country == "Netherlands")
    assert netherlands.person == "Joran"
    assert netherlands.number == 8
    sa = next(e for e in roster.entries if e.country == "South Africa")
    assert sa.number is None


def test_owners_by_country_handles_shared_team(tmp_path):
    path = _write(
        tmp_path,
        """
        people:
          Anh:
            - { country: France, number: 1 }
          Bennett:
            - { country: France, number: 99 }
            - { country: Ghana, number: 73 }
        """,
    )
    roster = Roster.load(path)
    owners = roster.owners_by_country()
    assert owners["France"] == ["Anh", "Bennett"]
    assert owners["Ghana"] == ["Bennett"]


def test_teams_by_person_preserves_order(tmp_path):
    path = _write(
        tmp_path,
        """
        people:
          Joran:
            - { country: Netherlands, number: 8 }
            - { country: Croatia, number: 11 }
          Rich:
            - { country: Brazil, number: 6 }
        """,
    )
    tbp = Roster.load(path).teams_by_person()
    assert tbp["Joran"] == ["Netherlands", "Croatia"]
    assert tbp["Rich"] == ["Brazil"]


def test_real_roster_loads():
    """The shipped roster.yaml parses and has the expected people."""
    from footballwatcher.config import PROJECT_ROOT

    roster = Roster.load(PROJECT_ROOT / "roster.yaml")
    people = {e.person for e in roster.entries}
    assert people == {
        "Barrett", "Joran", "Rich", "Sylvia", "Alanah", "Jackie", "Ash", "Tam", "David"
    }
    # Every entry has a country.
    assert all(e.country for e in roster.entries)
