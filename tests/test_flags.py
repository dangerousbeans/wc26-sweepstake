"""Country flag emoji lookup."""

from __future__ import annotations

from footballwatcher.flags import flag

NL = "\U0001F1F3\U0001F1F1"
CD = "\U0001F1E8\U0001F1E9"
US = "\U0001F1FA\U0001F1F8"


def test_direct_name():
    assert flag("Netherlands") == NL


def test_api_and_roster_spellings_match():
    assert flag("DR Congo") == CD
    assert flag("Congo DR") == CD
    assert flag("USA") == US
    assert flag("United States") == US
    assert flag("Cape Verde") == flag("Cape Verde Islands")
    assert flag("Bosnia & Herzegovina") == flag("Bosnia-Herzegovina")


def test_special_flag_england():
    assert flag("England").startswith("\U0001F3F4")  # tag-sequence flag


def test_unknown_returns_empty():
    assert flag("Atlantis") == ""
