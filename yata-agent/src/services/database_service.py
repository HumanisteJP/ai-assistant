from typing import Any, Dict, Optional
import json

from data.database_interface import DatabaseInterface


class DatabaseService:
    """
    データベース操作に関連するビジネスロジックを担当するサービスクラス。

    このクラスは、具体的なデータベース実装（Data層）から完全に独立しており、
    抽象的な`DatabaseInterface`にのみ依存します。
    """

    def __init__(self, db_engine: DatabaseInterface):
        """
        DatabaseServiceのインスタンスを初期化します。

        Args:
            db_engine (DatabaseInterface): データベース対話を担当するエンジン。
                                           DI（依存性注入）により外部から与えられる。
        """
        self._db_engine = db_engine

    def get_server_settings(self, guild_id: int) -> Optional[Dict[str, Any]]:
        """サーバー設定を取得します。"""
        return self._db_engine.get_server_settings(guild_id)

    def upsert_server_settings(
        self, guild_id: int, owner_id: int, gdrive_folder_id: str, language: str
    ) -> None:
        """サーバー設定を登録または更新します。"""
        self._db_engine.upsert_server_settings(
            guild_id, owner_id, gdrive_folder_id, language
        )

    def get_credentials(self, guild_id: int) -> Optional[Dict[str, Any]]:
        """認証情報を取得します。"""
        return self._db_engine.get_credentials(guild_id)

    def upsert_credentials(self, guild_id: int, token_dict: Dict[str, Any]) -> None:
        """
        認証情報を登録または更新します。
        Data層が永続化しやすいように、ここではデータ形式の変換は行わず、
        単純に処理を委譲します。
        """
        self._db_engine.upsert_credentials(guild_id, token_dict)

    def delete_server_data(self, guild_id: int) -> None:
        """サーバーに関連するすべてのデータを削除します。"""
        self._db_engine.delete_server_data(guild_id) 