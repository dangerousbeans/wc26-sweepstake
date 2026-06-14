# FootballWatcherBot

A cron-driven World Cup **sweepstake** tracker. Every run it pulls World Cup
fixtures from [football-data.org](https://www.football-data.org/), works out which
matches involve a sweepstake team, and emails a single digest to one address for
any alerts that are newly due. It also regenerates a static `dashboard.html` of the
full schedule. A small SQLite file remembers what's already been sent so reruns
don't duplicate.

## What it sends

- **Morning digest** — once per day (at/after a configured local hour), listing
  the day's tracked matches grouped under each match with the owner(s).
- **Pre-match nudge** — ~60 minutes before each tracked match kicks off.
- **Result + recap** — when a match goes FINISHED, with a brief natural-language
  recap written by Claude from the match events (falls back to a templated recap
  if the LLM call fails).

All alerts go to a single address (`EMAIL_TO`), labelled by person/team.

## Setup

1. **Python deps** (Python 3.11+):
   ```bash
   python3 -m venv .venv
   .venv/bin/pip install -r requirements.txt
   ```

2. **Config** — copy and fill in:
   ```bash
   cp .env.example .env
   ```
   You need:
   - `FOOTBALL_DATA_TOKEN` — free key from football-data.org.
   - `ANTHROPIC_API_KEY` — for match recaps (`SUMMARY_MODEL` defaults to `claude-opus-4-8`).
   - Gmail SMTP: `SMTP_USER` + `SMTP_PASSWORD` (a **Gmail App Password**, not your
     normal password — requires 2-Step Verification), and `EMAIL_TO`.

3. **Resolve teams** (one-time, needs the football-data token) — maps the roster
   country names to football-data.org team IDs and writes `teams.json`:
   ```bash
   .venv/bin/python -m footballwatcher.main resolve
   ```
   Check the output. Any country printed under **UNRESOLVED** needs an alias added
   to `ALIASES` in `footballwatcher/team_resolver.py` (the API sometimes uses a
   different spelling, e.g. "Congo DR" for "DR Congo"). Re-run `resolve` after
   editing. This is the one step that depends on the live API matching our names.

## Running

One cron tick (refresh data, regenerate dashboard, send any due alerts):
```bash
.venv/bin/python -m footballwatcher.main run
```

Just regenerate the dashboard (no emails):
```bash
.venv/bin/python -m footballwatcher.main dashboard
```

### Cron

Run every ~10 minutes. Example crontab entry (adjust the absolute path):
```
*/10 * * * * cd /home/joran/development/ai/FootballWatcherBot && .venv/bin/python -m footballwatcher.main run >> run.log 2>&1
```
A run that fails (API/SMTP/LLM error) exits non-zero **without** recording the
alert as sent, so the next run retries it.

## The roster

`roster.yaml` holds person → countries (with the draw number). Edit it freely;
re-run `resolve` if you add a country.

## Tests

```bash
.venv/bin/python -m pytest -q
```
Tests cover team resolution/aliases, the owner reverse-index, the "what's due"
dedup logic, template/dashboard rendering, match parsing, and the state store —
all against in-memory data, so they run without any secrets.

## Layout

```
footballwatcher/
  config.py         env/.env config
  roster.py         roster.yaml -> entries + owner reverse-index
  team_resolver.py  country name -> WC team id (alias table)
  football_data.py  API client + Match model
  state.py          SQLite dedup store
  alerts.py         pure "what's due" logic
  summarizer.py     Claude match recap (+ deterministic fallback)
  leaderboard.py    sweepstake scoring (Win 3 / Draw 1 per team owned)
  mailer.py         Jinja2 render + Gmail SMTP
  dashboard.py      static dashboard.html generator (schedule + floating leaderboard)
  main.py           orchestrator + CLI (run / resolve / dashboard)
  templates/        email + dashboard Jinja2 templates
tests/              pytest suite (no secrets needed)
```
