from enum import Enum, auto

from services.database_service import DatabaseService
from utils.messages import msg


class ReadinessLevel(Enum):
    NEED_SETUP = auto()
    NEED_AUTH = auto()
    READY = auto()


class ReadinessStatus:  # value object
    """Aggregated readiness information for a guild."""

    def __init__(self, level: ReadinessLevel):
        self.level = level

    @property
    def is_ready(self) -> bool:
        return self.level == ReadinessLevel.READY

    def guidance(self) -> str:
        """Return a user-friendly instruction in Japanese."""
        if self.level == ReadinessLevel.READY:
            return msg("ready")
        if self.level == ReadinessLevel.NEED_SETUP:
            return msg("need_setup")
        if self.level == ReadinessLevel.NEED_AUTH:
            return msg("need_auth")
        return "Unknown status"


class ReadinessService:
    """Business-logic layer component to check per-guild readiness."""

    def __init__(self, db_service: DatabaseService):
        self._db_service = db_service

    def check(self, guild_id: int) -> ReadinessStatus:
        """Return readiness level for *guild_id*."""
        settings = self._db_service.get_server_settings(guild_id)
        if not settings:
            return ReadinessStatus(ReadinessLevel.NEED_SETUP)

        creds = self._db_service.get_credentials(guild_id)
        if not creds:
            return ReadinessStatus(ReadinessLevel.NEED_AUTH)

        return ReadinessStatus(ReadinessLevel.READY) 