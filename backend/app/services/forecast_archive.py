"""Durable local archive of WINDFOR forecast revisions."""

from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Iterator

from app.services.data_normalization import normalize_timestamp


class ForecastRevisionArchive:
    """Persist source revisions so later evaluations do not depend on source retention."""

    def __init__(self, database_path: str | Path) -> None:
        self.database_path = Path(database_path)
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS forecast_revisions (
                    start_time TEXT NOT NULL,
                    publish_time TEXT NOT NULL,
                    record_json TEXT NOT NULL,
                    PRIMARY KEY (start_time, publish_time)
                )
                """
            )
            connection.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_forecast_revisions_publish_time
                ON forecast_revisions (publish_time)
                """
            )

    def store(self, records: list[dict]) -> None:
        """Insert or refresh revisions returned by Elexon."""
        if not records:
            return

        rows = []
        for record in records:
            start_time = _canonical_timestamp(record["startTime"])
            publish_time = _canonical_timestamp(record["publishTime"])
            rows.append(
                (
                    start_time,
                    publish_time,
                    json.dumps(record, separators=(",", ":"), sort_keys=True),
                )
            )

        with self._connect() as connection:
            connection.executemany(
                """
                INSERT INTO forecast_revisions (start_time, publish_time, record_json)
                VALUES (?, ?, ?)
                ON CONFLICT (start_time, publish_time)
                DO UPDATE SET record_json = excluded.record_json
                """,
                rows,
            )

    def load(self, publish_from: datetime, publish_to: datetime) -> list[dict]:
        """Load archived revisions in the inclusive UTC publication-time range."""
        start = _canonical_timestamp(publish_from)
        end = _canonical_timestamp(publish_to)
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT record_json
                FROM forecast_revisions
                WHERE publish_time >= ? AND publish_time <= ?
                ORDER BY publish_time, start_time
                """,
                (start, end),
            ).fetchall()
        return [json.loads(row[0]) for row in rows]

    @contextmanager
    def _connect(self) -> Iterator[sqlite3.Connection]:
        connection = sqlite3.connect(self.database_path, timeout=30)
        connection.execute("PRAGMA busy_timeout = 30000")
        try:
            yield connection
            connection.commit()
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()


def _canonical_timestamp(value: str | datetime) -> str:
    timestamp = normalize_timestamp(value)
    return timestamp.isoformat(timespec="microseconds").replace("+00:00", "Z")
