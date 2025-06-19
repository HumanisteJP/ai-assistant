import pytest
import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock
import discord

# projectのsrcディレクトリをパスに追加
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'src'))

# Python 3.8+ on Windows requires a specific asyncio policy for discord.py tests
# This is not strictly necessary on other platforms but doesn't hurt.
import asyncio
if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

# --- Mocks and Fixtures ---

# テスト対象のCogと、それが依存するService（のインターフェース）
# ファイルがまだ存在しないため、linterはエラーを出すが問題ない
from cogs.setup_cog import SetupCog
from services.database_service import DatabaseService


@pytest.fixture
def mock_db_service() -> MagicMock:
    """
    DatabaseServiceのモック（偽物）を提供するフィクスチャ。
    実際のDB接続の代わりに、メソッドがどのように呼ばれたかを記録する。
    """
    # spec=DatabaseService を指定することで、元のクラスに存在しないメソッドを
    # 呼び出そうとするとテストが失敗し、より安全なモックになる。
    return MagicMock(spec=DatabaseService)

@pytest.fixture
def setup_cog(mock_db_service: MagicMock) -> SetupCog:
    """
    テスト対象であるSetupCogのインスタンスを提供するフィクスチャ。
    依存性注入(DI)の原則に基づき、コンストラクタでモックのサービスを注入する。
    """
    return SetupCog(db_service=mock_db_service)


# --- Test Cases ---

@pytest.mark.asyncio
class TestSetupCog:
    """
    SetupCogのSlash Commandの挙動をテストする。
    """

    async def test_setup_command_success(self, setup_cog: SetupCog, mock_db_service: MagicMock):
        """
        /setupコマンドが正常に実行され、設定が保存されることをテストする。
        """
        # --- Arrange (準備) ---
        # discord.pyがコマンドハンドラに渡すApplicationContextオブジェクトのモックを作成
        mock_ctx = AsyncMock(spec=discord.ApplicationContext)
        mock_ctx.defer = AsyncMock()
        mock_ctx.followup = AsyncMock()
        mock_ctx.followup.send = AsyncMock()
        mock_ctx.guild.id = 12345
        mock_ctx.author.id = 67890

        # コマンドでユーザーが入力する引数
        gdrive_folder_id = "a_very_specific_google_drive_folder_id"
        language = "ja"

        # --- Act (実行) ---
        # Cogの持つSlash Commandのコールバックを直接呼び出す
        await setup_cog.setup.callback(setup_cog, mock_ctx, gdrive_folder_id=gdrive_folder_id, language=language)

        # --- Assert (検証) ---
        # 1. 依存するDatabaseServiceのメソッドが期待通りに呼び出されたか
        mock_db_service.upsert_server_settings.assert_called_once_with(
            guild_id=12345,
            owner_id=67890,
            gdrive_folder_id=gdrive_folder_id,
            language=language
        )

        # 2. Discordユーザーへの応答が正しく行われたか
        mock_ctx.followup.send.assert_called_once()
        # 応答メッセージの中身を検証
        args, kwargs = mock_ctx.followup.send.call_args
        assert "サーバー設定を保存しました" in kwargs.get("content", "")

    async def test_setup_command_db_error(self, setup_cog: SetupCog, mock_db_service: MagicMock):
        """
        データベース処理でエラーが発生した際に、ユーザーにエラーメッセージが返されることをテストする。
        """
        # --- Arrange (準備) ---
        mock_ctx = AsyncMock(spec=discord.ApplicationContext)
        mock_ctx.defer = AsyncMock()
        mock_ctx.followup = AsyncMock()
        mock_ctx.followup.send = AsyncMock()
        mock_ctx.guild.id = 12345
        mock_ctx.author.id = 67890
        gdrive_folder_id = "another_folder_id"
        language = "en"

        # モック化したサービスが、呼び出された際に例外を発生するように設定
        mock_db_service.upsert_server_settings.side_effect = Exception("Database connection failed")

        # --- Act (実行) ---
        await setup_cog.setup.callback(setup_cog, mock_ctx, gdrive_folder_id=gdrive_folder_id, language=language)

        # --- Assert (検証) ---
        # 1. エラーが発生しても、メソッドの呼び出し自体は試みられているはず
        mock_db_service.upsert_server_settings.assert_called_once_with(
            guild_id=12345,
            owner_id=67890,
            gdrive_folder_id=gdrive_folder_id,
            language=language
        )

        # 2. ユーザーにエラーを知らせる応答がされているか
        mock_ctx.followup.send.assert_called_once()
        args, kwargs = mock_ctx.followup.send.call_args
        assert "エラーが発生しました" in kwargs.get("content", "")
        assert "設定の保存に失敗しました" in kwargs.get("content", "")