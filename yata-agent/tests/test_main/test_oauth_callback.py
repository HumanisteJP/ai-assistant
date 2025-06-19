from unittest.mock import AsyncMock, MagicMock

from fastapi.testclient import TestClient

# FastAPI アプリと DI コンテナを import
from main import app, container  # type: ignore


def test_oauth_callback_triggers_google_service():
    """/oauth2callback が GoogleService.exchange_code_for_credentials を呼び出す。"""
    guild_id = 42
    code = "TEST_CODE"
    state = f"gid:{guild_id}"

    # GoogleService のモックを DI コンテナへ注入
    mock_google_service = MagicMock()
    mock_google_service.exchange_code_for_credentials = AsyncMock()
    container.google_service = mock_google_service  # type: ignore[attr-defined]

    client = TestClient(app)
    response = client.get("/oauth2callback", params={"code": code, "state": state})

    # ステータスコードと呼び出しを検証
    assert response.status_code == 200
    # AsyncMock は呼び出された後に 'assert_awaited_once_with' を使用
    mock_google_service.exchange_code_for_credentials.assert_awaited_once()
    mock_google_service.exchange_code_for_credentials.assert_awaited_once_with(guild_id=guild_id, code=code) 