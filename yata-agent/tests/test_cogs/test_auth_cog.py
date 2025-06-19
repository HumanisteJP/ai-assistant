import pytest
from unittest.mock import AsyncMock, MagicMock
import sys
from pathlib import Path

# Add src to path for test discovery when running direct file
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

import discord
from discord.ext import commands

# テスト対象のCog
from cogs.auth_cog import AuthCog
from services.google_service_interface import GoogleServiceInterface


@pytest.fixture
def mock_google_service() -> MagicMock:
    """GoogleServiceInterfaceのモックを生成するFixture。"""
    mock = MagicMock(spec=GoogleServiceInterface)
    mock.get_authentication_url = AsyncMock(return_value="https://auth.example.com")
    return mock


@pytest.fixture
def auth_cog(mock_google_service: MagicMock) -> AuthCog:
    """テスト対象のAuthCogインスタンスを生成するFixture。"""
    return AuthCog(google_service=mock_google_service)


@pytest.mark.asyncio
class TestAuthCog:
    """AuthCogのテストスイート。"""

    async def test_google_auth_sends_dm(
        self, auth_cog: AuthCog, mock_google_service: MagicMock
    ):
        """/google_authコマンドがDMで認証URLを送信することをテストする。"""
        # --- Arrange ---
        guild_id = 123
        state = f"gid:{guild_id}"
        
        # ApplicationContextのモックを作成
        mock_ctx = AsyncMock(spec=discord.ApplicationContext)
        mock_ctx.defer = AsyncMock()
        mock_ctx.followup = AsyncMock()
        mock_ctx.author.send = AsyncMock()  # DM送信用のモック
        mock_ctx.guild.id = guild_id

        # --- Act ---
        # `callback`を直接呼び出してコマンドのロジックを実行
        await auth_cog.google_auth.callback(auth_cog, mock_ctx)

        # --- Assert ---
        # 1. deferとfollowup.sendが呼ばれたか
        mock_ctx.defer.assert_awaited_once_with(ephemeral=True)
        
        # 2. 正しいstateで認証URL取得メソッドが呼ばれたか
        mock_google_service.get_authentication_url.assert_awaited_once_with(state=state)
        
        # 3. ユーザーのDMに認証URLが送信されたか
        mock_ctx.author.send.assert_awaited_once()
        sent_message = mock_ctx.author.send.call_args[0][0]
        assert "https://auth.example.com" in sent_message
        
        # 4. followupでユーザーに通知されたか
        mock_ctx.followup.send.assert_awaited_once_with(
            content="✅ 認証用のURLをダイレクトメッセージに送信しました。DMを確認してください。"
        ) 