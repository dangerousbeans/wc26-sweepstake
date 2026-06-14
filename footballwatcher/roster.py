"""Load the sweepstake roster and build a country -> owners reverse index."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import yaml


@dataclass(frozen=True)
class Entry:
    person: str
    country: str
    number: int | None


@dataclass
class Roster:
    entries: list[Entry] = field(default_factory=list)

    @classmethod
    def load(cls, path: Path) -> "Roster":
        data = yaml.safe_load(Path(path).read_text()) or {}
        people = data.get("people", {})
        entries: list[Entry] = []
        for person, picks in people.items():
            for pick in picks or []:
                entries.append(
                    Entry(
                        person=str(person),
                        country=str(pick["country"]),
                        number=pick.get("number"),
                    )
                )
        return cls(entries=entries)

    def countries(self) -> list[str]:
        """Unique country names in roster order (first appearance)."""
        seen: dict[str, None] = {}
        for e in self.entries:
            seen.setdefault(e.country, None)
        return list(seen.keys())

    def teams_by_person(self) -> dict[str, list[str]]:
        """person -> [country names], in roster (insertion) order."""
        index: dict[str, list[str]] = {}
        for e in self.entries:
            index.setdefault(e.person, []).append(e.country)
        return index

    def owners_by_country(self) -> dict[str, list[str]]:
        """country name -> [people who drew it], in roster order.

        A country can have multiple owners if it was drawn by more than one
        person (the reverse index handles that and is also what lets a single
        match be labelled with two owners).
        """
        index: dict[str, list[str]] = {}
        for e in self.entries:
            owners = index.setdefault(e.country, [])
            if e.person not in owners:
                owners.append(e.person)
        return index
