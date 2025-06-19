import json
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
import asyncio

from data.database_interface import DatabaseInterface
from .google_service_interface import GoogleServiceInterface

# Google APIのスコープ
SCOPES = [
    "https://www.googleapis.com/auth/documents",
    "https://www.googleapis.com/auth/drive"
]

class GoogleService(GoogleServiceInterface):
    """
    Google APIとの対話を行うサービス。
    """

    def __init__(
        self,
        db_service: DatabaseInterface,
        client_secrets_json: str,
        redirect_uri: str,
    ):
        """
        GoogleServiceのコンストラクタ。

        Args:
            db_service (DatabaseInterface): データベース対話のためのサービス。
            client_secrets_json (str): Google Cloudのクライアントシークレット(JSON形式)。
            redirect_uri (str): Google OAuth 2.0のリダイレクトURI。
        """
        self.db_service = db_service
        try:
            self.client_config = json.loads(client_secrets_json)
        except json.JSONDecodeError:
            raise ValueError("Invalid client_secrets_json format")
        self.redirect_uri = redirect_uri

    async def get_authentication_url(self, state: str) -> str:
        """ユーザー認証用のGoogle OAuth 2.0 URLを生成する。"""
        # この処理は同期的だが、インターフェースに合わせてasyncで定義
        flow = Flow.from_client_config(
            client_config=self.client_config, scopes=SCOPES, redirect_uri=self.redirect_uri
        )
        auth_url, _ = flow.authorization_url(
            access_type="offline",
            prompt="consent",
            state=state
        )
        return auth_url

    async def exchange_code_for_credentials(self, guild_id: int, code: str) -> None:
        """認証コードを資格情報に交換し、永続化する。"""
        # from_client_secrets_file は非同期ではないため、同期的に実行
        flow = Flow.from_client_config(
            client_config=self.client_config, scopes=SCOPES, redirect_uri=self.redirect_uri
        )
        # fetch_tokenはブロッキングI/Oのため、別スレッドで実行
        await asyncio.to_thread(flow.fetch_token, code=code)

        credentials = flow.credentials
        # DatabaseService is synchronous – run it in a thread to avoid
        # blocking the event loop.  ``credentials.to_json`` returns a JSON
        # string so we parse it back into a dict for storage.
        import json as _json

        await asyncio.to_thread(
            self.db_service.upsert_credentials,
            guild_id,
            _json.loads(credentials.to_json()),
        )

    async def upload_document(self, guild_id: int, title: str, content: str) -> str:
        """Googleドキュメントを作成し、指定された内容でアップロードする。"""
        # DatabaseService is *sync* so we must run calls in a thread.
        credentials_json = await asyncio.to_thread(
            self.db_service.get_credentials,
            guild_id,
        )
        if not credentials_json:
            raise ValueError(f"No valid credentials found for guild {guild_id}")

        settings = await asyncio.to_thread(
            self.db_service.get_server_settings,
            guild_id,
        )
        folder_id = settings.get("gdrive_folder_id") if settings else None

        # ``credentials_json`` can be stored as *dict* or JSON str depending on
        # the database backend.  Accept both formats for robustness.
        if isinstance(credentials_json, str):
            creds_dict = json.loads(credentials_json)
        else:  # already a dict-like object
            creds_dict = credentials_json

        creds = Credentials.from_authorized_user_info(creds_dict)

        # Google APIのクライアントはブロッキングI/Oのため、to_threadで実行
        def _execute_api_calls():
            try:
                docs_service = build("docs", "v1", credentials=creds)
                drive_service = build("drive", "v3", credentials=creds)

                # 1. ドキュメント作成
                doc = docs_service.documents().create(body={"title": title}).execute()
                doc_id = doc["documentId"]

                # 2. コンテンツ挿入
                requests = [{"insertText": {"location": {"index": 1}, "text": content}}]
                docs_service.documents().batchUpdate(
                    documentId=doc_id, body={"requests": requests}
                ).execute()

                # 3. フォルダ移動
                if folder_id:
                    file = drive_service.files().get(fileId=doc_id, fields='parents').execute()
                    previous_parents = ",".join(file.get('parents', []))
                    drive_service.files().update(
                        fileId=doc_id, addParents=folder_id, removeParents=previous_parents
                    ).execute()
                
                return f"https://docs.google.com/document/d/{doc_id}/edit"

            except HttpError as e:
                # エラーをキャッチして、より具体的な情報とともに再送出
                raise Exception(f"Google API Error: {e.reason}") from e

        return await asyncio.to_thread(_execute_api_calls) 