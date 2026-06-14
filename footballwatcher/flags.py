"""Country -> emoji flag, tolerant of both our roster names and the API's names.

Lookup is by normalised name (same normaliser as team resolution), so e.g.
"DR Congo", "Congo DR", "USA", "United States", "Cape Verde", "Cape Verde
Islands" all resolve. Unknown names return "" (the template just omits the flag).
"""

from __future__ import annotations

from .team_resolver import normalize

# Special flags that aren't simple ISO-3166 regional-indicator pairs.
_SPECIAL = {
    "england": "\U0001F3F4\U000E0067\U000E0062\U000E0065\U000E006E\U000E0067\U000E007F",
    "scotland": "\U0001F3F4\U000E0067\U000E0062\U000E0073\U000E0063\U000E0074\U000E007F",
    "wales": "\U0001F3F4\U000E0067\U000E0062\U000E0077\U000E006C\U000E0073\U000E007F",
}

# Normalised name -> ISO 3166-1 alpha-2. Includes roster spellings, the API
# spellings we resolved, and likely opponents.
_ISO2 = {
    # roster nations (our spelling + the API spelling)
    "jordan": "JO", "ghana": "GH", "mexico": "MX", "uruguay": "UY", "iraq": "IQ",
    "paraguay": "PY", "cape verde": "CV", "cape verde islands": "CV", "cabo verde": "CV",
    "netherlands": "NL", "croatia": "HR", "south africa": "ZA", "sweden": "SE",
    "bosnia and herzegovina": "BA", "bosnia herzegovina": "BA", "bosnia": "BA",
    "ivory coast": "CI", "cote d ivoire": "CI", "colombia": "CO", "austria": "AT",
    "brazil": "BR", "qatar": "QA", "uzbekistan": "UZ", "portugal": "PT", "belgium": "BE",
    "morocco": "MA", "saudi arabia": "SA", "tunisia": "TN", "iran": "IR", "ir iran": "IR",
    "usa": "US", "united states": "US", "czechia": "CZ", "czech republic": "CZ",
    "panama": "PA", "egypt": "EG", "switzerland": "CH", "new zealand": "NZ", "nz": "NZ",
    "algeria": "DZ", "curacao": "CW", "canada": "CA", "france": "FR", "spain": "ES",
    "argentina": "AR", "haiti": "HT", "dr congo": "CD", "congo dr": "CD",
    "democratic republic of the congo": "CD", "south korea": "KR", "korea republic": "KR",
    "senegal": "SN", "japan": "JP", "australia": "AU",
    # common opponents / other likely 2026 qualifiers
    "germany": "DE", "turkey": "TR", "turkiye": "TR", "ecuador": "EC", "chile": "CL",
    "peru": "PE", "bolivia": "BO", "venezuela": "VE", "italy": "IT", "norway": "NO",
    "denmark": "DK", "poland": "PL", "ukraine": "UA", "serbia": "RS", "greece": "GR",
    "hungary": "HU", "slovakia": "SK", "slovenia": "SI", "romania": "RO", "nigeria": "NG",
    "cameroon": "CM", "mali": "ML", "costa rica": "CR", "honduras": "HN", "jamaica": "JM",
    "china": "CN", "china pr": "CN", "thailand": "TH", "united arab emirates": "AE", "uae": "AE",
    "oman": "OM", "bahrain": "BH", "new caledonia": "NC", "bolivia": "BO",
    "panama": "PA", "guatemala": "GT", "el salvador": "SV", "trinidad and tobago": "TT",
    "scotland": None, "wales": None, "england": None,  # handled via _SPECIAL
}


def _iso2_to_emoji(code: str) -> str:
    return "".join(chr(0x1F1E6 + ord(c) - ord("A")) for c in code.upper())


def flag(name: str) -> str:
    """Return the emoji flag for a country name, or '' if unknown."""
    n = normalize(name)
    if n in _SPECIAL:
        return _SPECIAL[n]
    code = _ISO2.get(n)
    return _iso2_to_emoji(code) if code else ""
