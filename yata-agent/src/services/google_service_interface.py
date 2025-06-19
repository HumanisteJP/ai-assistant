from abc import ABC, abstractmethod


class GoogleServiceInterface(ABC):
    """
    Google API（認証、Drive、Docs）との対話を抽象化するインターフェース。
    """

    @abstractmethod
    async def get_authentication_url(self, state: str) -> str:
        """
        ユーザー認証用のGoogle OAuth 2.0 URLを生成する。

        Args:
            state (str): CSRF対策およびコールバック時の状態識別のための文字列。

        Returns:
            str: ユーザーをリダイレクトさせるための認証URL。
        """
        pass

    @abstractmethod
    async def exchange_code_for_credentials(self, guild_id: int, code: str) -> None:
        """
        認証コードを資格情報（アクセストークン、リフレッシュトークン）に交換し、永続化する。

        Args:
            guild_id (int): 資格情報を紐付けるDiscordサーバーのID。
            code (str): OAuth 2.0コールバックで受け取った認証コード。

        Raises:
            Exception: トークンの交換や保存に失敗した場合。
        """
        pass

    @abstractmethod
    async def upload_document(self, guild_id: int, title: str, content: str) -> str:
        """
        Googleドキュメントを作成し、指定された内容でアップロードする。

        Args:
            guild_id (int): 使用する資格情報と設定が紐付いたDiscordサーバーのID。
            title (str): 作成するGoogleドキュメントのタイトル。
            content (str): ドキュメントに書き込むテキスト内容。

        Returns:
            str: 作成されたGoogleドキュメントのURL。

        Raises:
            ValueError: 有効な資格情報がサーバーに登録されていない場合。
            Exception: ドキュメントの作成やアップロードに失敗した場合。
        """
        pass 