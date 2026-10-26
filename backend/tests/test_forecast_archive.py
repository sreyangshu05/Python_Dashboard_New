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
