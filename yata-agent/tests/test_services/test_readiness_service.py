import pytest
from unittest.mock import MagicMock

from services.readiness_service import ReadinessService, ReadinessLevel
from services.database_service import DatabaseService


class TestReadinessService:
    @pytest.fixture
    def mock_db(self) -> MagicMock:
        return MagicMock(spec=DatabaseService)

    @pytest.fixture
    def service(self, mock_db: MagicMock) -> ReadinessService:
        return ReadinessService(db_service=mock_db)

    def test_need_setup(self, service: ReadinessService, mock_db: MagicMock):
        mock_db.get_server_settings.return_value = None
        status = service.check(1)
        assert status.level == ReadinessLevel.NEED_SETUP

    def test_need_auth(self, service: ReadinessService, mock_db: MagicMock):
        mock_db.get_server_settings.return_value = {"guild_id": 1}
        mock_db.get_credentials.return_value = None
        status = service.check(1)
        assert status.level == ReadinessLevel.NEED_AUTH

    def test_ready(self, service: ReadinessService, mock_db: MagicMock):
        mock_db.get_server_settings.return_value = {"guild_id": 1}
        mock_db.get_credentials.return_value = {"token": "x"}
        status = service.check(1)
        assert status.level == ReadinessLevel.READY 