# Data and Evaluation Methodology

## Source and scope

The application uses only Elexon BMRS `FUELHH` actual generation filtered to
`fuelType=WIND` and `WINDFOR` forecast publications. The configured evaluation
period is January 1–31, 2026. Source timestamps are parsed as timezone-aware
UTC. No demand, weather, price, or generated production data is used.

- [FUELHH stream documentation](https://bmrs.elexon.co.uk/api-documentation/endpoint/datasets/FUELHH/stream)
- [WINDFOR stream documentation](https://bmrs.elexon.co.uk/api-documentation/endpoint/datasets/WINDFOR/stream)

The application requests a bounded publication-time range. A live request for
January 2026 returned 20,440 WINDFOR records and 1,536 FUELHH WIND records.
These are observations from the API during the validation run, not a promise of
future source retention or identical future responses. Every successfully
retrieved WINDFOR revision is also recorded in a local SQLite archive, keyed by
target and publication time. Later evaluations merge the current Elexon
response with archived revisions before applying the decision cutoff. Docker
Compose stores this database in the persistent `windscope-data` volume.

The archive preserves records from the first successful fetch of each
publication window onward; it does not reconstruct revisions that were already
unavailable before the first fetch. Archive durability depends on retaining the
configured database file or Docker volume and maintaining backups.

## Target and decision timestamps

`startTime` identifies the target period; `publishTime` identifies when a
forecast revision became available. For target hour `T`, the default
day-ahead decision is 09:00 UTC on the preceding calendar day. The selector
chooses the forecast with the greatest publication time satisfying
`publishTime <= decision_time`. A forecast first published after the cutoff is
not selected. A publication exactly at the cutoff is eligible under this
documented inclusive policy.

An observed source example: for target `2026-01-15T12:00:00Z`, the Jan 14
`07:30Z` revision of `11,049 MW` was the latest publication returned at or
before the Jan 14 `09:00Z` cutoff. The `09:30Z` revision (`11,178 MW`) was
excluded. These values document that target only.

Evaluation dates are UTC calendar days and include each hourly target in the
half-open interval from start-of-first-day to start-of-day-after-end. A day
with missing source records still yields explicit unavailable hourly records.
The decision date is separate from the target/evaluation date.

## Resolution and missing-data policy

FUELHH records are half-hourly and WINDFOR records are hourly. Records are
deduplicated by actual `startTime`, retaining the latest actual publication.
Only hours with both half-hour periods are averaged for the hourly actual;
incomplete hours are excluded and counted, never padded or treated as zero.
Identical forecast `(startTime, publishTime)` duplicates are removed, while
revisions with different publication times are retained.

Null, non-numeric, NaN, and infinite generation values are excluded during
normalization and counted. Missing forecasts and actuals remain `null`.
MAE/RMSE/MBE/MAPE use finite matched forecast/actual pairs. MAPE also excludes
zero actuals; it is `null` if there are no non-zero actual values.

## Metrics

With signed error `e = forecast - actual`:

- MAE = mean(`abs(e)`) in MW.
- RMSE = square root of mean(`e²`) in MW.
- MBE = mean(`e`) in MW; positive means overforecast.
- MAPE = mean(`abs(e) / abs(actual)`) × 100 over non-zero actuals.

The API reports total, valid, missing-forecast, missing-actual, non-finite,
MAPE-eligible, and zero-actual-excluded observation counts. Empty metric sets
return null metric values rather than fabricated zeros.

## Interpretation limits

These metrics describe forecast error, not procurement cost, imbalance cash
out, or financial savings. Hourly averaging masks within-hour ramps. Although
the validation request confirmed multiple historical revisions for a tested
January period, the application cannot guarantee that Elexon returned every revision
when a publication window was first captured or detect future changes to
source semantics. The local archive protects only records that were actually
captured. The dashboard has been manually checked in a local browser; no
external deployment has been verified.
