"""Service configuration from environment."""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from cfi_registry import RegistryStore
    from cfi_registry.db import PostgresRegistryStore


@dataclass
class ServiceConfig:
    database_url: str
    minimum_cohort_k: int = 10
    host: str = "127.0.0.1"
    port: int = 8000

    @classmethod
    def from_env(cls) -> ServiceConfig:
        return cls(
            database_url=os.getenv(
                "CFI_DATABASE_URL",
                "sqlite:///./cfi_registry.db",
            ),
            minimum_cohort_k=int(os.getenv("CFI_MINIMUM_COHORT_K", "10")),
            host=os.getenv("CFI_HOST", "127.0.0.1"),
            port=int(os.getenv("CFI_PORT", "8000")),
        )


def create_registry_store(config: ServiceConfig | None = None) -> RegistryStore | PostgresRegistryStore:
    """Factory: SQLite/Postgres when URL set, else in-memory."""
    from cfi_registry import RegistryStore
    from cfi_registry.db import PostgresRegistryStore

    config = config or ServiceConfig.from_env()
    url = config.database_url
    if url.startswith("memory://"):
        return RegistryStore()
    return PostgresRegistryStore(url)
