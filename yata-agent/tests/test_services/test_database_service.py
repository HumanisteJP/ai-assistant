import pytest
import sys
from pathlib import Path
from typing import Any, Dict, Optional

# プロジェクトのsrcディレクトリをパスに追加
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'src'))

# これから作成するモジュール（まだ存在しないため、テストはここで失敗する）
from services.database_service import DatabaseService
from data.database_interface import DatabaseInterface

# --- テスト用のモックオブジェクト ---
class MockDatabase(DatabaseInterface):
    """
    DatabaseInterfaceの偽物（モック）実装。
    実際のDBには接続せず、メモリ上の辞書で状態を管理する。
    """
    def __init__(self):
        self._servers: Dict[int, Dict[str, Any]] = {}
        self._credentials: Dict[int, Dict[str, Any]] = {}

    def get_server_settings(self, guild_id: int) -> Optional[Dict[str, Any]]:
        return self._servers.get(guild_id)

    def upsert_server_settings(self, guild_id: int, owner_id: int, gdrive_folder_id: str, language: str):
        self._servers[guild_id] = {
            "guild_id": guild_id,
            "owner_id": owner_id,
            "gdrive_folder_id": gdrive_folder_id,
            "language": language
        }

    def get_credentials(self, guild_id: int) -> Optional[Dict[str, Any]]:
        # Service層との契約通り、辞書を直接返す
        return self._credentials.get(guild_id)

    def upsert_credentials(self, guild_id: int, token_dict: Dict[str, Any]):
        # Service層との契約通り、辞書を直接受け取る
        if guild_id not in self._servers:
            raise ValueError("Foreign key constraint failed")
        self._credentials[guild_id] = token_dict

    def delete_server_data(self, guild_id: int):
        if guild_id in self._servers:
            del self._servers[guild_id]
        if guild_id in self._credentials:
            del self._credentials[guild_id]

# --- テスト本体 ---
@pytest.fixture
def mock_db() -> MockDatabase:
    """MockDatabaseのインスタンスを提供するフィクスチャ。"""
    return MockDatabase()

@pytest.fixture
def db_service(mock_db: MockDatabase) -> DatabaseService:
    """テスト対象のDatabaseServiceインスタンスを提供するフィクスチャ。"""
    return DatabaseService(db_engine=mock_db)

class TestDatabaseService:
    """DatabaseServiceのビジネスロジックをテストする。"""

    def test_get_and_upsert_server_settings(self, db_service: DatabaseService, mock_db: MockDatabase):
        """サーバー設定の登録と取得をテストする。"""
        guild_id = 123
        # 最初は存在しない
        assert db_service.get_server_settings(guild_id) is None

        # 登録する
        db_service.upsert_server_settings(guild_id, 456, "folder_abc", "en")

        # 取得できることを確認
        settings = db_service.get_server_settings(guild_id)
        assert settings is not None
        assert settings["gdrive_folder_id"] == "folder_abc"
        assert mock_db._servers[guild_id]["language"] == "en" # モックの内部状態も確認

    def test_get_and_upsert_credentials(self, db_service: DatabaseService):
        """認証情報の登録と取得をテストする。"""
        guild_id = 123
        # 先にサーバーを登録しておく
        db_service.upsert_server_settings(guild_id, 456, "folder_abc", "en")
        
        # 最初は存在しない
        assert db_service.get_credentials(guild_id) is None

        # 登録する
        creds_dict = {"token": "abc", "refresh_token": "def"}
        db_service.upsert_credentials(guild_id, creds_dict)

        # 取得できることを確認
        retrieved_creds = db_service.get_credentials(guild_id)
        assert retrieved_creds is not None
        assert retrieved_creds["token"] == "abc"

    def test_upsert_credentials_fails_if_server_does_not_exist(self, db_service: DatabaseService):
        """認証情報の登録は、対応するサーバーが存在しない場合に失敗することをテストする。"""
        guild_id = 789  # このサーバーは存在しない
        # db_engine(MockDatabase)が送出するValueErrorをそのまま上位に伝播させるはず
        with pytest.raises(ValueError):
            db_service.upsert_credentials(guild_id, {"token": "some_token"})

    def test_delete_server_data(self, db_service: DatabaseService):
        """サーバー関連データがすべて削除されることをテストする。"""
        guild_id = 123
        db_service.upsert_server_settings(guild_id, 456, "folder_abc", "en")
        db_service.upsert_credentials(guild_id, {"token": "abc"})

        # 存在することを確認
        assert db_service.get_server_settings(guild_id) is not None
        assert db_service.get_credentials(guild_id) is not None

        # 削除する
        db_service.delete_server_data(guild_id)

        # 削除されたことを確認
        assert db_service.get_server_settings(guild_id) is None
        assert db_service.get_credentials(guild_id) is None
