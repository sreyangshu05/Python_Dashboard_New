from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone

from app.services.forecast_archive import ForecastRevisionArchive


def _record(start_time: str, publish_time: str, generation: float) -> dict:
    return {
        "startTime": start_time,
        "publishTime": publish_time,
        "generation": generation,
    }


def test_archive_survives_reopening_and_deduplicates_retrieved_revisions(tmp_path):
    database_path = tmp_path / "windfor.sqlite3"
    first_record = _record(
        "2026-01-15T12:00:00Z", "2026-01-14T07:30:00Z", 5200.0
    )
    archive = ForecastRevisionArchive(database_path)

    archive.store([first_record, first_record])
    reopened_archive = ForecastRevisionArchive(database_path)
    records = reopened_archive.load(
        datetime(2026, 1, 14, tzinfo=timezone.utc),
        datetime(2026, 1, 15, tzinfo=timezone.utc),
    )

    assert records == [first_record]


def test_archive_filters_by_inclusive_publication_time_in_utc(tmp_path):
    archive = ForecastRevisionArchive(tmp_path / "windfor.sqlite3")
    records = [
        _record("2026-01-15T12:00:00Z", "2026-01-13T23:59:59Z", 5100.0),
        _record("2026-01-15T12:00:00Z", "2026-01-14T07:30:00Z", 5200.0),
        _record("2026-01-15T12:00:00Z", "2026-01-15T00:00:00Z", 5300.0),
    ]
    archive.store(records)

    loaded = archive.load(
        datetime(2026, 1, 14, tzinfo=timezone.utc),
        datetime(2026, 1, 15, tzinfo=timezone.utc),
    )

    assert loaded == [records[1], records[2]]


def test_concurrent_archive_access_serializes_sqlite_transactions(tmp_path):
    database_path = tmp_path / "windfor.sqlite3"
    archives = [ForecastRevisionArchive(database_path) for _ in range(8)]
    records_by_worker = [
        [
            _record(
                f"2026-01-{worker + 1:02d}T{index // 60:02d}:{index % 60:02d}:00Z",
                f"2026-01-{worker + 1:02d}T07:30:00Z",
                float(index),
            )
            for index in range(100)
        ]
        for worker in range(len(archives))
    ]
    publish_from = datetime(2026, 1, 1, tzinfo=timezone.utc)
    publish_to = datetime(2026, 1, 31, tzinfo=timezone.utc)

    with ThreadPoolExecutor(max_workers=len(archives)) as executor:
        list(
            executor.map(
                lambda worker: archives[worker].store(records_by_worker[worker]),
                range(len(archives)),
            )
        )

    records = archives[0].load(publish_from, publish_to)
    expected_records = {
        (record["startTime"], record["publishTime"])
        for records in records_by_worker
        for record in records
    }
    loaded_keys = {
        (record["startTime"], record["publishTime"])
        for record in records
    }
    assert loaded_keys == expected_records
