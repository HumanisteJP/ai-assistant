from abc import ABC, abstractmethod
from typing import Any, Dict, Optional


class DatabaseInterface(ABC):
    """
    データ永続化層の操作に関するインターフェース。

    このインターフェースは、ビジネスロジック（Service層）とデータアクセス
    （Data層）を分離するための「契約」を定義します。Service層は、この
    インターフェースのメソッドを通じてのみデータにアクセスし、SQLなどの
    具体的な実装の詳細からは完全に独立します。
    """

    @abstractmethod
    def get_server_settings(self, guild_id: int) -> Optional[Dict[str, Any]]:
        """
        指定されたDiscordサーバー（Guild）の設定を取得します。

        Args:
            guild_id (int): DiscordサーバーのID。

        Returns:
            Optional[Dict[str, Any]]: サーバー設定を含む辞書。
                                      見つからない場合はNone。
        """
        pass

    @abstractmethod
    def upsert_server_settings(
        self, guild_id: int, owner_id: int, gdrive_folder_id: str, language: str
    ) -> None:
        """
        サーバー設定を登録または更新（Upsert）します。

        Args:
            guild_id (int): DiscordサーバーのID。
            owner_id (int): 設定を所有するユーザーのID。
            gdrive_folder_id (str): Google DriveのフォルダID。
            language (str): 使用言語。
        """
        pass

    @abstractmethod
    def get_credentials(self, guild_id: int) -> Optional[Dict[str, Any]]:
        """
        指定されたサーバーの認証情報を取得します。
        保存されているJSON文字列は辞書にパースして返却します。

        Args:
            guild_id (int): DiscordサーバーのID。

        Returns:
            Optional[Dict[str, Any]]: 認証情報を含む辞書。
                                      見つからない場合はNone。
        """
        pass

    @abstractmethod
    def upsert_credentials(self, guild_id: int, token_dict: Dict[str, Any]) -> None:
        """
        サーバーの認証情報を登録または更新（Upsert）します。
        引数で受け取った辞書はJSON文字列として保存します。

        Args:
            guild_id (int): DiscordサーバーのID。
            token_dict (Dict[str, Any]): OAuthトークンなどを含む認証情報の辞書。
        """
        pass

    @abstractmethod
    def delete_server_data(self, guild_id: int) -> None:
        """
        指定されたサーバーに関連するすべてのデータ（設定、認証情報）を削除します。

        Args:
            guild_id (int): DiscordサーバーのID。
        """
        pass 