"""Team resolution + alias handling."""

from __future__ import annotations

from footballwatcher.team_resolver import normalize, resolve_countries


API_TEAMS = [
    {"id": 1, "name": "United States", "tla": "USA"},
    {"id": 2, "name": "Czech Republic", "tla": "CZE"},
    {"id": 3, "name": "Korea Republic", "tla": "KOR"},
    {"id": 4, "name": "Congo DR", "tla": "COD"},
    {"id": 5, "name": "Côte d'Ivoire", "tla": "CIV"},
    {"id": 6, "name": "Cabo Verde", "tla": "CPV"},
    {"id": 7, "name": "IR Iran", "tla": "IRN"},
    {"id": 8, "name": "Bosnia and Herzegovina", "tla": "BIH"},
    {"id": 9, "name": "New Zealand", "tla": "NZL"},
    {"id": 10, "name": "Curaçao", "tla": "CUW"},
    {"id": 11, "name": "Netherlands", "tla": "NED"},
]


def test_normalize_strips_accents_and_punctuation():
    assert normalize("Côte d'Ivoire") == "cote d ivoire"
    assert normalize("Bosnia & Herzegovina") == "bosnia and herzegovina"
    assert normalize("Curaçao") == "curacao"


def test_resolves_direct_names():
    result = resolve_countries(["Netherlands"], API_TEAMS)
    assert result.resolved["Netherlands"] == 11
    assert not result.unresolved


def test_resolves_via_aliases():
    roster = [
        "USA",
        "Czechia",
        "South Korea",
        "DR Congo",
        "Ivory Coast",
        "Cape Verde",
        "Iran",
        "Bosnia & Herzegovina",
        "New Zealand",
        "Curaçao",
    ]
    result = resolve_countries(roster, API_TEAMS)
    assert result.unresolved == []
    assert result.resolved["USA"] == 1
    assert result.resolved["Czechia"] == 2
    assert result.resolved["South Korea"] == 3
    assert result.resolved["DR Congo"] == 4
    assert result.resolved["Ivory Coast"] == 5
    assert result.resolved["Cape Verde"] == 6
    assert result.resolved["Iran"] == 7
    assert result.resolved["Bosnia & Herzegovina"] == 8
    assert result.resolved["Curaçao"] == 10


def test_unresolved_reported():
    result = resolve_countries(["Atlantis"], API_TEAMS)
    assert result.unresolved == ["Atlantis"]
    assert "Atlantis" not in result.resolved


def test_team_names_populated_for_tracked():
    result = resolve_countries(["USA"], API_TEAMS)
    assert result.team_names[1] == "United States"
