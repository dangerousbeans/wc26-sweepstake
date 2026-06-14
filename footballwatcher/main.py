"""Orchestrator + CLI for one cron run.

Commands:
  resolve    Fetch WC teams, map roster countries -> team IDs, save teams.json.
  run        One cron tick: refresh data, regenerate dashboard, send due alerts.
  dashboard  Regenerate dashboard.html only (no emails).
"""

from __future__ import annotations

import argparse
import logging
import sys
from datetime import datetime, timezone

from . import alerts
from .config import Config
from .dashboard import write_dashboard
from .football_data import FootballDataClient, Match
from .mailer import Mailer
from .roster import Roster
from .state import StateStore
from .summarizer import Summarizer, fallback_summary
from .team_resolver import (
    ResolveResult,
    load_teams,
    resolve_countries,
    save_teams,
)

log = logging.getLogger("footballwatcher")


def _now() -> datetime:
    return datetime.now(timezone.utc)


def cmd_resolve(cfg: Config) -> int:
    cfg_token = cfg.football_data_token
    if not cfg_token:
        log.error("FOOTBALL_DATA_TOKEN is required for `resolve`.")
        return 2
    roster = Roster.load(_roster_path(cfg))
    client = FootballDataClient(cfg_token)
    api_teams = client.list_teams(cfg.competition_code)
    result = resolve_countries(roster.countries(), api_teams)
    save_teams(cfg.teams_file, result)

    print(f"Resolved {len(result.resolved)} / {len(roster.countries())} countries.")
    for country, tid in result.resolved.items():
        print(f"  ✓ {country:<26} -> {result.team_names.get(tid)} (id {tid})")
    if result.unresolved:
        print("\nUNRESOLVED (add an alias in team_resolver.ALIASES):")
        for country in result.unresolved:
            print(f"  ✗ {country}")
    print(f"\nSaved {cfg.teams_file}")
    return 0


def _load_or_resolve_teams(cfg: Config) -> ResolveResult:
    if cfg.teams_file.exists():
        return load_teams(cfg.teams_file)
    log.info("teams.json missing; resolving teams from the API.")
    roster = Roster.load(_roster_path(cfg))
    client = FootballDataClient(cfg.football_data_token)
    api_teams = client.list_teams(cfg.competition_code)
    result = resolve_countries(roster.countries(), api_teams)
    save_teams(cfg.teams_file, result)
    return result


def _roster_path(cfg: Config):
    from .config import PROJECT_ROOT

    return PROJECT_ROOT / "roster.yaml"


def _team_owners(roster: Roster, teams: ResolveResult) -> dict[int, list[str]]:
    """team id -> [owners], via roster country -> owners and country -> team id."""
    owners_by_country = roster.owners_by_country()
    index: dict[int, list[str]] = {}
    for country, tid in teams.resolved.items():
        index.setdefault(tid, [])
        for person in owners_by_country.get(country, []):
            if person not in index[tid]:
                index[tid].append(person)
    return index


def _prepare(
    cfg: Config,
) -> tuple[list[Match], dict[int, list[str]], list[str], list[tuple[str, list[str]]]]:
    roster = Roster.load(_roster_path(cfg))
    teams = _load_or_resolve_teams(cfg)
    team_owners = _team_owners(roster, teams)
    tracked_ids = set(teams.resolved.values())
    people = sorted({e.person for e in roster.entries})
    picks = list(roster.teams_by_person().items())

    client = FootballDataClient(cfg.football_data_token)
    all_matches = client.list_matches(cfg.competition_code)
    tracked = alerts.tracked_matches(all_matches, tracked_ids)
    alerts.attach_owners(tracked, team_owners)
    return tracked, team_owners, people, picks


def cmd_dashboard(cfg: Config) -> int:
    tracked, _, people, picks = _prepare(cfg)
    path = write_dashboard(
        cfg.dashboard_file, tracked, _now(),
        timezone=cfg.timezone, people=people, picks=picks,
    )
    print(f"Dashboard written: {path} ({len(tracked)} matches)")
    return 0


def cmd_run(cfg: Config) -> int:
    cfg.require_for_run()
    tracked, _, people, picks = _prepare(cfg)

    # Always refresh the dashboard so it reflects the latest data.
    write_dashboard(
        cfg.dashboard_file, tracked, _now(),
        timezone=cfg.timezone, people=people, picks=picks,
    )

    mailer = Mailer(
        host=cfg.smtp_host,
        port=cfg.smtp_port,
        user=cfg.smtp_user,
        password=cfg.smtp_password,
        email_from=cfg.email_from,
        email_to=cfg.email_to,
        timezone=cfg.timezone,
    )
    summarizer = Summarizer(cfg.anthropic_api_key, cfg.summary_model)

    sent = 0
    with StateStore(cfg.state_db) as state:
        plan = alerts.determine_due(
            tracked,
            state,
            _now(),
            timezone=cfg.timezone,
            morning_digest_hour=cfg.morning_digest_hour,
            prematch_lead_minutes=cfg.prematch_lead_minutes,
        )

        if plan.digest_date:
            email = mailer.render(
                "morning_digest",
                subject=f"⚽ World Cup today — {len(plan.digest_matches)} of our matches",
                digest_date=plan.digest_date,
                matches=plan.digest_matches,
            )
            mailer.send(email)
            state.mark_digest_sent(plan.digest_date)
            sent += 1
            log.info("Sent morning digest for %s", plan.digest_date)

        for m in plan.prematch:
            email = mailer.render(
                "prematch",
                subject=f"⏰ Soon: {m.home_name} vs {m.away_name}",
                match=m,
            )
            mailer.send(email)
            state.mark_prematch_sent(m.id)
            sent += 1
            log.info("Sent pre-match nudge for match %s", m.id)

        for m in plan.results:
            try:
                summary = summarizer.summarize(m)
            except Exception as exc:  # noqa: BLE001 - degrade gracefully, still email
                log.warning("Summary failed for match %s (%s); using fallback.", m.id, exc)
                summary = fallback_summary(m)
            email = mailer.render(
                "result",
                subject=f"🏁 {m.home_name} {m.home_score}-{m.away_score} {m.away_name}",
                match=m,
                summary=summary,
            )
            mailer.send(email)
            state.mark_result_sent(m.id)
            sent += 1
            log.info("Sent result for match %s", m.id)

    print(f"Run complete. {len(tracked)} tracked matches, {sent} alert(s) sent.")
    return 0


def main(argv: list[str] | None = None) -> int:
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s"
    )
    parser = argparse.ArgumentParser(prog="footballwatcher")
    parser.add_argument(
        "command",
        nargs="?",
        default="run",
        choices=["run", "resolve", "dashboard"],
    )
    args = parser.parse_args(argv)
    cfg = Config.from_env()

    try:
        if args.command == "resolve":
            return cmd_resolve(cfg)
        if args.command == "dashboard":
            return cmd_dashboard(cfg)
        return cmd_run(cfg)
    except Exception as exc:  # noqa: BLE001 - top-level: log and exit non-zero so cron retries
        log.error("Run failed: %s", exc, exc_info=True)
        return 1


if __name__ == "__main__":
    sys.exit(main())
