"""WindScope UK Backend Configuration."""

import os
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class Settings:
    """Application settings loaded from environment variables."""

    # Elexon API
    ELEXON_BASE_URL: str = field(
        default_factory=lambda: os.getenv(
            "ELEXON_BASE_URL", "https://data.elexon.co.uk/bmrs/api/v1"
        )
    )
    ELEXON_TIMEOUT_SECONDS: int = field(
        default_factory=lambda: int(os.getenv("ELEXON_TIMEOUT_SECONDS", "30"))
    )
    ELEXON_MAX_RETRIES: int = field(
        default_factory=lambda: int(os.getenv("ELEXON_MAX_RETRIES", "3"))
    )

    # Evaluation period
    EVALUATION_START: str = field(
        default_factory=lambda: os.getenv("EVALUATION_START", "2026-01-01")
    )
    EVALUATION_END: str = field(
        default_factory=lambda: os.getenv("EVALUATION_END", "2026-01-31")
    )

    # Default decision cutoff hour (UTC) — e.g., 09:00 UTC for day-ahead decisions
    DEFAULT_DECISION_HOUR_UTC: int = field(
        default_factory=lambda: int(os.getenv("DEFAULT_DECISION_HOUR_UTC", "9"))
    )

    # Cache TTL in seconds (default 15 minutes)
    CACHE_TTL_SECONDS: int = field(
        default_factory=lambda: int(os.getenv("CACHE_TTL_SECONDS", "900"))
    )

    # Persistent snapshot of WINDFOR revisions retrieved from Elexon
    WINDFOR_ARCHIVE_PATH: str = field(
        default_factory=lambda: os.getenv(
            "WINDFOR_ARCHIVE_PATH",
            str(Path(__file__).resolve().parents[1] / "data" / "windfor.sqlite3"),
        )
    )

    # CORS
    CORS_ORIGINS: list[str] = field(
        default_factory=lambda: os.getenv(
            "CORS_ORIGINS", "http://localhost:5173,http://localhost:3000,http://localhost:8080"
        ).split(",")
    )

    # Server
    HOST: str = field(default_factory=lambda: os.getenv("HOST", "0.0.0.0"))
    PORT: int = field(default_factory=lambda: int(os.getenv("PORT", "8000")))


settings = Settings()
