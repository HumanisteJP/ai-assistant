import pytest
import sqlite3
import json
from pathlib import Path
import sys
from typing import Iterator

# projectのsrcディレクトリをパスに追加
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'src'))

# テスト対象のクラスとインターフェース
from data.database import Database, init_db
from data.database_interface import DatabaseInterface

DB_PATH = ":memory:"

@pytest.fixture
def db() -> Iterator[Database]:
    """テストごとにインメモリDBで初期化されたDatabaseインスタンスを提供する。"""
    # インメモリDBは接続ごとに独立しているため、同じ接続を共有する必要がある
    conn = sqlite3.connect(DB_PATH)
    # まずテーブルを初期化
    init_db(connection=conn)
    # 同じ接続を使ってDatabaseインスタンスを作成
    db_instance = Database(db_path=DB_PATH, connection=conn)
    yield db_instance
    db_instance.close()

class TestDatabaseImplementation:
    """DatabaseクラスがInterfaceを実装し、CRUD操作を正しく行うことをテストする。"""

    def test_database_adheres_to_interface(self):
        """DatabaseクラスがDatabaseInterfaceに準拠しているか確認する。"""
        assert issubclass(Database, DatabaseInterface)

    def test_upsert_and_get_server_settings(self, db: Database):
        """サーバー設定の登録・更新と取得をテストする。"""
        # 1. 新規登録
        db.upsert_server_settings(
            guild_id=1, owner_id=100, gdrive_folder_id="folder1", language="en"
        )
        settings = db.get_server_settings(guild_id=1)
        assert settings is not None
        assert settings["gdrive_folder_id"] == "folder1"
        assert settings["language"] == "en"

        # 2. 更新（Upsert）
        db.upsert_server_settings(
            guild_id=1, owner_id=101, gdrive_folder_id="folder_updated", language="ja"
        )
        updated_settings = db.get_server_settings(guild_id=1)
        assert updated_settings is not None
        assert updated_settings["owner_id"] == 101
        assert updated_settings["gdrive_folder_id"] == "folder_updated"
        assert updated_settings["language"] == "ja"

    def test_get_non_existent_server_settings(self, db: Database):
        """存在しないサーバー設定の取得でNoneが返ることをテストする。"""
        assert db.get_server_settings(guild_id=999) is None

    def test_upsert_and_get_credentials(self, db: Database):
        """認証情報の登録・更新と取得をテストする。"""
        # 外部キー制約のため、先にサーバーを登録する必要がある
        db.upsert_server_settings(guild_id=1, owner_id=100, gdrive_folder_id="f", language="en")

        # 1. 新規登録
        creds_dict = {"token": "abc", "refresh_token": "def"}
        db.upsert_credentials(guild_id=1, token_dict=creds_dict)
        retrieved_creds = db.get_credentials(guild_id=1)
        assert retrieved_creds is not None
        assert retrieved_creds["token"] == "abc"

        # 2. 更新 (Upsert)
        updated_creds_dict = {"token": "xyz", "scopes": ["email"]}
        db.upsert_credentials(guild_id=1, token_dict=updated_creds_dict)
        retrieved_updated_creds = db.get_credentials(guild_id=1)
        assert retrieved_updated_creds is not None
        assert retrieved_updated_creds["token"] == "xyz"
        assert "refresh_token" not in retrieved_updated_creds  # 新しい辞書で上書きされる

    def test_upsert_credentials_fails_without_server(self, db: Database):
        """サーバーが存在しない場合、認証情報の登録に失敗することをテストする。"""
        with pytest.raises(sqlite3.IntegrityError):
            db.upsert_credentials(guild_id=999, token_dict={"token": "abc"})

    def test_delete_server_data(self, db: Database):
        """サーバーデータ削除（カスケード削除）をテストする。"""
        # データを作成
        db.upsert_server_settings(guild_id=1, owner_id=100, gdrive_folder_id="f", language="en")
        db.upsert_credentials(guild_id=1, token_dict={"token": "abc"})

        # 存在する事を確認
        assert db.get_server_settings(guild_id=1) is not None
        assert db.get_credentials(guild_id=1) is not None

        # 削除を実行
        db.delete_server_data(guild_id=1)

        # 削除された事を確認
        assert db.get_server_settings(guild_id=1) is None
        # 外部キーのカスケード削除により、こちらもNoneになるはず
        assert db.get_credentials(guild_id=1) is None 