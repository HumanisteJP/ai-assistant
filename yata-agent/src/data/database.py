import sqlite3
import json
from typing import Any, Dict, Optional, Tuple, List

from .database_interface import DatabaseInterface


def init_db(connection: sqlite3.Connection):
    """
    指定された接続を使用して、データベースのテーブルを初期化します。
    """
    cursor = connection.cursor()
    # サーバー設定テーブル
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS servers (
            guild_id INTEGER PRIMARY KEY,
            owner_id INTEGER NOT NULL,
            gdrive_folder_id TEXT,
            language TEXT NOT NULL DEFAULT 'ja'
        );
    """)
    # 認証情報テーブル
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS credentials (
            guild_id INTEGER PRIMARY KEY,
            token_json TEXT NOT NULL,
            FOREIGN KEY (guild_id) REFERENCES servers (guild_id) ON DELETE CASCADE
        );
    """)
    connection.commit()
    # この関数は接続を閉じない


class Database(DatabaseInterface):
    """
    SQLiteデータベースとの対話を担当する具象クラス。
    DatabaseInterfaceの契約を実装します。
    """
    def __init__(self, db_path: str, connection: Optional[sqlite3.Connection] = None):
        """
        データベースへの接続を初期化します。

        Args:
            db_path (str): データベースファイルのパス。インメモリDBの場合は":memory:"を指定。
            connection (Optional[sqlite3.Connection]): 既存のsqlite3.Connectionオブジェクト。
        """
        self.db_path = db_path
        try:
            if connection:
                self.conn = connection
            else:
                # ``check_same_thread=False`` allows the same connection
                # object to be used from worker threads spawned via
                # ``asyncio.to_thread``.  SQLite itself is threadsafe as
                # long as *each* connection is used in a serialized way.
                # Our application serialises access via the GIL and short
                # transactions, so this setting is acceptable here.
                self.conn = sqlite3.connect(db_path, check_same_thread=False)
            
            self.conn.row_factory = sqlite3.Row
            self.conn.execute("PRAGMA foreign_keys = ON")

            # Ensure tables exist (safe thanks to IF NOT EXISTS)
            try:
                init_db(self.conn)
            except sqlite3.Error as e:
                print(f"Failed to initialise database schema: {e}")
                raise
        except sqlite3.Error as e:
            print(f"Database connection error: {e}")
            raise

    def close(self) -> None:
        """データベース接続を閉じます。"""
        if self.conn:
            self.conn.close()

    def _execute_query(self, query: str, params: Tuple = ()) -> None:
        """内部用のクエリ実行メソッド。"""
        try:
            self.conn.execute(query, params)
            self.conn.commit()
        except sqlite3.Error as e:
            print(f"Database query failed: {e}")
            self.conn.rollback()
            raise

    def _fetch_one(self, query: str, params: Tuple = ()) -> Optional[Dict[str, Any]]:
        """内部用の単一レコード取得メソッド。"""
        cursor = self.conn.cursor()
        cursor.execute(query, params)
        row = cursor.fetchone()
        return dict(row) if row else None

    def get_server_settings(self, guild_id: int) -> Optional[Dict[str, Any]]:
        query = "SELECT * FROM servers WHERE guild_id = ?"
        return self._fetch_one(query, (guild_id,))

    def upsert_server_settings(
        self, guild_id: int, owner_id: int, gdrive_folder_id: str, language: str
    ) -> None:
        query = """
            INSERT INTO servers (guild_id, owner_id, gdrive_folder_id, language)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(guild_id) DO UPDATE SET
                owner_id = excluded.owner_id,
                gdrive_folder_id = excluded.gdrive_folder_id,
                language = excluded.language
        """
        self._execute_query(query, (guild_id, owner_id, gdrive_folder_id, language))

    def get_credentials(self, guild_id: int) -> Optional[Dict[str, Any]]:
        query = "SELECT token_json FROM credentials WHERE guild_id = ?"
        result = self._fetch_one(query, (guild_id,))
        if result and result.get("token_json"):
            return json.loads(result["token_json"])
        return None

    def upsert_credentials(self, guild_id: int, token_dict: Dict[str, Any]) -> None:
        token_json = json.dumps(token_dict)
        query = """
            INSERT INTO credentials (guild_id, token_json)
            VALUES (?, ?)
            ON CONFLICT(guild_id) DO UPDATE SET
                token_json = excluded.token_json
        """
        self._execute_query(query, (guild_id, token_json))

    def delete_server_data(self, guild_id: int) -> None:
        # ON DELETE CASCADEにより、serversから削除すればcredentialsも削除される
        query = "DELETE FROM servers WHERE guild_id = ?"
        self._execute_query(query, (guild_id,))

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
