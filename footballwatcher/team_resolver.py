"""Map roster country names to football-data.org team IDs.

football-data.org uses its own canonical team names which don't always match the
names we drew (e.g. "USA" vs "United States", "DR Congo" vs "Congo DR"). This
module normalises names and uses an alias table to bridge the gap, then resolves
each roster country to the API's numeric team id.

This is the one step that must be verified against the live API the first time —
run `python -m footballwatcher.main resolve` to see which countries resolved and
which need an alias added below.
"""

from __future__ import annotations

import json
import unicodedata
from dataclasses import dataclass
from pathlib import Path


def normalize(name: str) -> str:
    """Lowercase, strip accents and punctuation, normalise '&'/'and', collapse spaces."""
    nfkd = unicodedata.normalize("NFKD", name)
    ascii_only = "".join(c for c in nfkd if not unicodedata.combining(c))
    ascii_only = ascii_only.lower().replace("&", " and ")
    cleaned = []
    for ch in ascii_only:
        if ch.isalnum() or ch.isspace():
            cleaned.append(ch)
        else:
            cleaned.append(" ")
    return " ".join("".join(cleaned).split())


# Roster display name -> additional accepted API names. The normalised display
# name itself is always tried first, so only the *divergent* API spellings need
# to be listed here. Add to this table when `resolve` reports an unresolved name.
ALIASES: dict[str, list[str]] = {
    "USA": ["United States", "United States of America", "USA"],
    "Czechia": ["Czech Republic"],
    "South Korea": ["Korea Republic", "Republic of Korea"],
    "DR Congo": ["Congo DR", "Democratic Republic of the Congo", "Congo", "Congo DR (Zaire)"],
    "Ivory Coast": ["Côte d'Ivoire", "Cote d'Ivoire"],
    "Cape Verde": ["Cabo Verde"],
    "Iran": ["IR Iran", "Iran (Islamic Republic of)"],
    "Bosnia & Herzegovina": ["Bosnia and Herzegovina", "Bosnia-Herzegovina"],
    "New Zealand": ["NZ"],
    "Curaçao": ["Curacao"],
    "Qatar": ["State of Qatar"],
    "Türkiye": ["Turkey", "Turkiye"],
}


@dataclass
class ResolveResult:
    # roster country name -> API team id
    resolved: dict[str, int]
    # roster country names that could not be matched
    unresolved: list[str]
    # API team id -> canonical API name (for tracked teams)
    team_names: dict[int, str]


def build_name_lookup(api_teams: list[dict]) -> dict[str, dict]:
    """normalised API team name -> the API team dict."""
    lookup: dict[str, dict] = {}
    for team in api_teams:
        for key in ("name", "shortName", "tla"):
            value = team.get(key)
            if value:
                lookup.setdefault(normalize(value), team)
    return lookup


def resolve_countries(countries: list[str], api_teams: list[dict]) -> ResolveResult:
    """Match each roster country to an API team.

    Order of attempts per country: normalised display name, then each alias.
    """
    lookup = build_name_lookup(api_teams)
    resolved: dict[str, int] = {}
    unresolved: list[str] = []
    team_names: dict[int, str] = {}

    for country in countries:
        candidates = [country, *ALIASES.get(country, [])]
        match = None
        for candidate in candidates:
            match = lookup.get(normalize(candidate))
            if match:
                break
        if match and match.get("id") is not None:
            tid = int(match["id"])
            resolved[country] = tid
            team_names[tid] = match.get("name", country)
        else:
            unresolved.append(country)

    return ResolveResult(resolved=resolved, unresolved=unresolved, team_names=team_names)


def save_teams(path: Path, result: ResolveResult) -> None:
    payload = {
        "resolved": result.resolved,
        "unresolved": result.unresolved,
        "team_names": {str(k): v for k, v in result.team_names.items()},
    }
    Path(path).write_text(json.dumps(payload, indent=2, ensure_ascii=False))


def load_teams(path: Path) -> ResolveResult:
    payload = json.loads(Path(path).read_text())
    return ResolveResult(
        resolved={k: int(v) for k, v in payload.get("resolved", {}).items()},
        unresolved=list(payload.get("unresolved", [])),
        team_names={int(k): v for k, v in payload.get("team_names", {}).items()},
    )
