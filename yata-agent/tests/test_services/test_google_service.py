import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import json

from services.google_service import GoogleService
from services.google_service_interface import GoogleServiceInterface
from data.database_interface import DatabaseInterface

# テスト対象のモジュールパス
SERVICE_PATH = "services.google_service"

@pytest.fixture
def mock_db_interface() -> MagicMock:
    """DatabaseInterfaceのモックを生成するFixture。"""
    mock = MagicMock(spec=DatabaseInterface)
    # DatabaseInterface defines synchronous methods. For GoogleService which
    # calls them via ``asyncio.to_thread`` we can keep them as synchronous
    # MagicMocks.
    mock.get_credentials = MagicMock()
    mock.upsert_credentials = MagicMock()
    mock.get_server_settings = MagicMock()
    return mock

class TestGoogleService:
    """GoogleServiceのテストスイート。"""

    def test_conforms_to_interface(self, mock_db_interface: MagicMock):
        """GoogleServiceがGoogleServiceInterfaceを実装していることを確認する。"""
        assert isinstance(
            GoogleService(
                db_service=mock_db_interface,
                client_secrets_json='{}',
                redirect_uri='http://localhost'
            ),
            GoogleServiceInterface
        )

    @pytest.mark.asyncio
    async def test_get_authentication_url(self, mock_db_interface: MagicMock):
        """認証URLが正しく生成されることをテストする。"""
        # --- Arrange ---
        # from_client_secrets_file のモック
        mock_flow = MagicMock()
        mock_flow.authorization_url.return_value = ("https://example.com/auth", "test_state")
        
        with patch(f"{SERVICE_PATH}.Flow.from_client_config", return_value=mock_flow) as mock_from_config:
            client_secrets_dict = {"web": {"client_id": "test"}}
            service = GoogleService(
                db_service=mock_db_interface,
                client_secrets_json=json.dumps(client_secrets_dict),
                redirect_uri='http://localhost/callback'
            )
            
            # --- Act ---
            auth_url = await service.get_authentication_url(state="test_state")

            # --- Assert ---
            mock_from_config.assert_called_once()
            # 呼び出し時の scopes と redirect_uri を検証
            _, kwargs = mock_from_config.call_args
            assert kwargs['client_config'] == client_secrets_dict
            assert "https://www.googleapis.com/auth/drive" in kwargs['scopes']
            assert kwargs['redirect_uri'] == 'http://localhost/callback'
            
            # authorization_url が正しい引数で呼び出されたか
            mock_flow.authorization_url.assert_called_once_with(
                access_type='offline',
                prompt='consent',
                state='test_state'
            )
            # 戻り値が期待通りか
            assert auth_url == "https://example.com/auth"
            
    @pytest.mark.asyncio
    async def test_exchange_code_for_credentials(self, mock_db_interface: MagicMock):
        """認証コードが資格情報に交換され、DBに保存されることをテストする。"""
        # --- Arrange ---
        guild_id = 12345
        auth_code = "dummy_auth_code"
        
        # Flowのモック設定
        mock_flow = MagicMock()
        # fetch_tokenはto_threadで呼ばれる同期的メソッドなので、通常のMagicMockで十分
        mock_flow.fetch_token = MagicMock() 
        
        # 資格情報のモック
        mock_creds = MagicMock()
        mock_creds.to_json.return_value = '{"token": "dummy", "refresh_token": "dummy_refresh"}'
        mock_flow.credentials = mock_creds

        # from_client_secrets_file がモックフローを返すように設定
        with patch(f"{SERVICE_PATH}.Flow.from_client_config", return_value=mock_flow) as mock_from_config:
            service = GoogleService(
                db_service=mock_db_interface,
                client_secrets_json='{"web": {}}',
                redirect_uri='http://localhost'
            )
            
            # --- Act ---
            await service.exchange_code_for_credentials(guild_id=guild_id, code=auth_code)

            # --- Assert ---
            # トークン取得処理が正しいコードで呼ばれたか
            mock_flow.fetch_token.assert_called_once_with(code=auth_code)
            # DBへの保存処理が正しい引数で呼ばれたか
            mock_db_interface.upsert_credentials.assert_called_once_with(
                guild_id,
                json.loads(mock_creds.to_json())
            )

    @pytest.mark.asyncio
    async def test_upload_document_no_credentials(self, mock_db_interface: MagicMock):
        """資格情報がない場合にValueErrorを送出するかテストする。"""
        # --- Arrange ---
        mock_db_interface.get_credentials.return_value = None  # 資格情報がない状態を模倣
        service = GoogleService(
            db_service=mock_db_interface,
            client_secrets_json='{}',
            redirect_uri='http://localhost'
        )
        
        # --- Act & Assert ---
        with pytest.raises(ValueError, match="No valid credentials found for guild"):
            await service.upload_document(guild_id=123, title="Test", content="Hello")
            
    @pytest.mark.asyncio
    async def test_upload_document_success(self, mock_db_interface: MagicMock):
        """ドキュメントのアップロードが成功するケースをテストする。"""
        # --- Arrange ---
        guild_id = 123
        folder_id = "test_folder_id"
        doc_id = "test_doc_id"
        doc_url = f"https://docs.google.com/document/d/{doc_id}/edit"

        # DBモックの設定
        mock_db_interface.get_credentials.return_value = '{"token": "dummy"}'
        mock_db_interface.get_server_settings.return_value = {"gdrive_folder_id": folder_id}

        # Google APIクライアントのモック
        mock_creds = MagicMock()

        # Docs と Drive のサービスリソースを作成
        mock_docs_service = MagicMock()
        mock_drive_service = MagicMock()

        # docs_service.documents() が返すリソースを明示的に用意
        docs_resource = MagicMock()
        mock_docs_service.documents.return_value = docs_resource

        # create().execute() の戻り値
        docs_resource.create.return_value.execute.return_value = {"documentId": doc_id}

        # batchUpdate().execute() をモック
        docs_resource.batchUpdate.return_value.execute.return_value = {}

        # drive_service.files() リソースを設定
        drive_files_resource = MagicMock()
        mock_drive_service.files.return_value = drive_files_resource

        drive_files_resource.get.return_value.execute.return_value = {"parents": ["old_parent_id"]}
        drive_files_resource.update.return_value.execute.return_value = {}

        # build が呼ばれたときの戻り値を設定
        def build_side_effect(serviceName, version, credentials):
            if serviceName == "docs":
                return mock_docs_service
            if serviceName == "drive":
                return mock_drive_service
            return MagicMock()
        
        # build自体は関数なので、MagicMockでパッチする
        with patch(f"{SERVICE_PATH}.Credentials.from_authorized_user_info", return_value=mock_creds), \
             patch(f"{SERVICE_PATH}.build", side_effect=build_side_effect) as mock_build:
            
            service = GoogleService(db_service=mock_db_interface, client_secrets_json='{}', redirect_uri='')
            
            # --- Act ---
            result_url = await service.upload_document(guild_id, "Test Title", "Hello World")
            
            # --- Assert ---
            # ドキュメント作成が呼ばれたか
            docs_resource.create.assert_called_once_with(body={"title": "Test Title"})
            # コンテンツ挿入が呼ばれたか
            docs_resource.batchUpdate.assert_called_once()
            # フォルダ移動が呼ばれたか
            drive_files_resource.update.assert_called_once_with(
                fileId=doc_id, addParents=folder_id, removeParents="old_parent_id"
            )
            # 戻り値が正しいか
            assert result_url == doc_url 