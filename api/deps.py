"""Shared API dependencies — singletons and common utilities for routers"""

from core.config import ConfigManager
from database.connection import get_db_connection

# Shared ConfigManager singleton — preserves save-dedup cache across requests
_config_manager: ConfigManager | None = None


def get_config_manager() -> ConfigManager:
    """Return the shared ConfigManager instance (created once per process)."""
    global _config_manager
    if _config_manager is None:
        _config_manager = ConfigManager(get_db_connection)
    return _config_manager
