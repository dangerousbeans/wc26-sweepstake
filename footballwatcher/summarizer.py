"""Generate a brief natural-language match recap from structured event data."""

from __future__ import annotations

import anthropic

from .football_data import Match


def _score_line(match: Match) -> str:
    if match.home_score is None or match.away_score is None:
        return f"{match.home_name} vs {match.away_name} (score unavailable)"
    return (
        f"{match.home_name} {match.home_score}-{match.away_score} {match.away_name}"
    )


def _facts(match: Match) -> str:
    lines = [f"Final score: {_score_line(match)}"]
    if match.stage:
        lines.append(f"Stage: {match.stage}")
    if match.group:
        lines.append(f"Group: {match.group}")
    if match.scorers:
        goals = ", ".join(
            f"{s.name}" + (f" {s.minute}'" if s.minute is not None else "")
            + (f" ({s.team})" if s.team else "")
            for s in match.scorers
        )
        lines.append(f"Goals: {goals}")
    else:
        lines.append("Goalscorer details: not available.")
    if match.home_owners:
        lines.append(f"{match.home_name} is owned by: {', '.join(match.home_owners)}")
    if match.away_owners:
        lines.append(f"{match.away_name} is owned by: {', '.join(match.away_owners)}")
    return "\n".join(lines)


def fallback_summary(match: Match) -> str:
    """Deterministic recap used if the LLM call is unavailable or fails."""
    parts = [f"Full time: {_score_line(match)}."]
    if match.scorers:
        parts.append(
            "Scorers — "
            + "; ".join(
                f"{s.name}" + (f" ({s.minute}')" if s.minute is not None else "")
                for s in match.scorers
            )
            + "."
        )
    return " ".join(parts)


class Summarizer:
    def __init__(self, api_key: str, model: str = "claude-opus-4-8"):
        self._client = anthropic.Anthropic(api_key=api_key)
        self._model = model

    def summarize(self, match: Match) -> str:
        prompt = (
            "Write a brief (2-4 sentence) recap of this FIFA World Cup match for a "
            "sweepstake alert email. Be lively but accurate. Mention the scoreline and "
            "any key goalscorers. If a team is owned by a sweepstake participant, you "
            "may nod to how their team did. Do not invent facts not given below.\n\n"
            f"{_facts(match)}"
        )
        response = self._client.messages.create(
            model=self._model,
            max_tokens=600,
            messages=[{"role": "user", "content": prompt}],
        )
        text = "".join(
            block.text for block in response.content if block.type == "text"
        ).strip()
        return text or fallback_summary(match)
