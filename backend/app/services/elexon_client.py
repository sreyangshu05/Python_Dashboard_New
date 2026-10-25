"""Elexon BMRS API client for FUELHH and WINDFOR datasets."""

from __future__ import annotations

import logging
import time
from datetime import datetime, timezone
from typing import Any

import httpx

from app.config import settings

logger = logging.getLogger(__name__)


class ElexonAPIError(Exception):
    """Raised when Elexon API returns an error or unexpected response."""
    pass


class ElexonClient:
    """Client for the Elexon BMRS data API.

    Provides methods to fetch FUELHH (actual generation) and WINDFOR (forecast)
    data with retry logic, timeout handling, and response validation.
    """

    def __init__(self) -> None:
        self.base_url = settings.ELEXON_BASE_URL
        self.timeout = settings.ELEXON_TIMEOUT_SECONDS
        self.max_retries = settings.ELEXON_MAX_RETRIES
        self._last_fetch_time: datetime | None = None

    @property
    def last_fetch_time(self) -> datetime | None:
        return self._last_fetch_time

    def _make_request(self, endpoint: str, params: dict[str, Any]) -> list[dict]:
        """Make a GET request with retry logic.

        Args:
            endpoint: API path relative to base URL.
            params: Query parameters.

        Returns:
            Parsed JSON response (list of records).

        Raises:
            ElexonAPIError: On non-recoverable API errors.
        """
        url = f"{self.base_url}/{endpoint}"
        last_error: Exception | None = None

        for attempt in range(1, self.max_retries + 1):
            try:
                with httpx.Client(timeout=self.timeout) as client:
                    logger.info(
                        "Elexon API request attempt %d/%d: %s",
                        attempt, self.max_retries, endpoint,
                    )
                    response = client.get(url, params=params, headers={"Accept": "application/json"})

                    if response.status_code == 429:
                        wait_time = min(2 ** attempt, 30)
                        logger.warning("Rate limited. Waiting %ds before retry.", wait_time)
                        time.sleep(wait_time)
                        continue

                    response.raise_for_status()
                    data = response.json()

                    if not isinstance(data, list):
                        raise ElexonAPIError(
                            f"Expected list response from {endpoint}, got {type(data).__name__}"
                        )

                    self._last_fetch_time = datetime.now(timezone.utc)
                    logger.info("Fetched %d records from %s", len(data), endpoint)
                    return data

            except httpx.TimeoutException as e:
                last_error = e
                logger.warning("Timeout on attempt %d for %s: %s", attempt, endpoint, e)
                if attempt < self.max_retries:
                    time.sleep(min(2 ** attempt, 10))
            except httpx.HTTPStatusError as e:
                last_error = e
                if e.response.status_code >= 500:
                    logger.warning("Server error %d on attempt %d", e.response.status_code, attempt)
                    if attempt < self.max_retries:
                        time.sleep(min(2 ** attempt, 10))
                else:
                    raise ElexonAPIError(
                        f"HTTP {e.response.status_code} from Elexon API: {e.response.text[:200]}"
                    ) from e
            except ElexonAPIError:
                raise
            except Exception as e:
                last_error = e
                logger.error("Unexpected error fetching %s: %s", endpoint, e)
                if attempt < self.max_retries:
                    time.sleep(min(2 ** attempt, 10))

        raise ElexonAPIError(
            f"Failed to fetch {endpoint} after {self.max_retries} attempts: {last_error}"
        )

    def fetch_actual_wind_generation(
        self,
        publish_from: datetime,
        publish_to: datetime,
    ) -> list[dict]:
        """Fetch actual wind generation (FUELHH, fuelType=WIND).

        Uses publishDateTimeFrom/To to filter by the publication time of actuals.
        FUELHH publishes actuals roughly at the end of each settlement period.

        Args:
            publish_from: Start of publishDateTime range (UTC).
            publish_to: End of publishDateTime range (UTC).

        Returns:
            List of FUELHH WIND records.
        """
        params = {
            "publishDateTimeFrom": publish_from.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "publishDateTimeTo": publish_to.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "fuelType": "WIND",
        }
        return self._make_request("datasets/FUELHH/stream", params)

    def fetch_wind_forecasts(
        self,
        publish_from: datetime,
        publish_to: datetime,
    ) -> list[dict]:
        """Fetch wind generation forecasts (WINDFOR) by publication time.

        Using publishDateTimeFrom/To preserves all historical forecast revisions,
        which is essential for reconstructing what was available at a historical
        decision time.

        Args:
            publish_from: Start of publishDateTime range (UTC).
            publish_to: End of publishDateTime range (UTC).

        Returns:
            List of WINDFOR records with publishTime and startTime.
        """
        params = {
            "publishDateTimeFrom": publish_from.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "publishDateTimeTo": publish_to.strftime("%Y-%m-%dT%H:%M:%SZ"),
        }
        return self._make_request("datasets/WINDFOR/stream", params)

