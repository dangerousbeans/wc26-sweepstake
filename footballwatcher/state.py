"""SQLite-backed dedup store so cron reruns don't send duplicate alerts."""

from __future__ import annotations

import sqlite3
from pathlib import Path


class StateStore:
    def __init__(self, path: Path):
        self._conn = sqlite3.connect(str(path))
        self._conn.row_factory = sqlite3.Row
        self._init_schema()

    def _init_schema(self) -> None:
        self._conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS match_alerts (
                match_id     INTEGER PRIMARY KEY,
                prematch_sent INTEGER NOT NULL DEFAULT 0,
                result_sent   INTEGER NOT NULL DEFAULT 0
            );
            CREATE TABLE IF NOT EXISTS sent_digests (
                digest_date TEXT PRIMARY KEY
            );
            """
        )
        self._conn.commit()

    # --- pre-match ---
    def prematch_sent(self, match_id: int) -> bool:
        row = self._conn.execute(
            "SELECT prematch_sent FROM match_alerts WHERE match_id = ?", (match_id,)
        ).fetchone()
        return bool(row and row["prematch_sent"])

    def mark_prematch_sent(self, match_id: int) -> None:
        self._conn.execute(
            """
            INSERT INTO match_alerts (match_id, prematch_sent) VALUES (?, 1)
            ON CONFLICT(match_id) DO UPDATE SET prematch_sent = 1
            """,
            (match_id,),
        )
        self._conn.commit()

    # --- result ---
    def result_sent(self, match_id: int) -> bool:
        row = self._conn.execute(
            "SELECT result_sent FROM match_alerts WHERE match_id = ?", (match_id,)
        ).fetchone()
        return bool(row and row["result_sent"])

    def mark_result_sent(self, match_id: int) -> None:
        self._conn.execute(
            """
            INSERT INTO match_alerts (match_id, result_sent) VALUES (?, 1)
            ON CONFLICT(match_id) DO UPDATE SET result_sent = 1
            """,
            (match_id,),
        )
        self._conn.commit()

    # --- morning digest ---
    def digest_sent(self, digest_date: str) -> bool:
        row = self._conn.execute(
            "SELECT 1 FROM sent_digests WHERE digest_date = ?", (digest_date,)
        ).fetchone()
        return row is not None

    def mark_digest_sent(self, digest_date: str) -> None:
        self._conn.execute(
            "INSERT OR IGNORE INTO sent_digests (digest_date) VALUES (?)",
            (digest_date,),
        )
        self._conn.commit()

    def close(self) -> None:
        self._conn.close()

    def __enter__(self) -> "StateStore":
        return self

    def __exit__(self, *exc) -> None:
        self.close()
