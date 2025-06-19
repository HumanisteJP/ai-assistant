import pytest
from unittest.mock import AsyncMock, MagicMock, patch, mock_open

from services.transcription_service import TranscriptionService
from services.transcription_service_interface import TranscriptionServiceInterface

# テスト対象のモジュールパス
SERVICE_PATH = "services.transcription_service"

@pytest.fixture
def mock_openai_client() -> MagicMock:
    """OpenAIの非同期クライアントのモックを生成するFixture。"""
    mock_client = MagicMock()
    mock_transcriptions = MagicMock()
    # createメソッドをAsyncMockに設定
    mock_transcriptions.create = AsyncMock()
    mock_client.audio.transcriptions = mock_transcriptions
    return mock_client

class TestTranscriptionService:
    """TranscriptionServiceのテストスイート。"""

    def test_conforms_to_interface(self):
        """TranscriptionServiceがTranscriptionServiceInterfaceを実装していることを確認する。"""
        # 具象クラスのインスタンスがインターフェースのインスタンスでもあることを確認
        assert isinstance(TranscriptionService(api_key="dummy_key"), TranscriptionServiceInterface)

    @pytest.mark.asyncio
    async def test_transcribe_success(self, mock_openai_client: MagicMock):
        """文字起こしが正常に完了するケースをテストする。"""
        # --- Arrange ---
        # モックの設定
        api_key = "test_api_key"
        audio_path = "/path/to/fake/audio.mp3"
        expected_text = "これはテストです。"
        
        # client.audio.transcriptions.create の戻り値を設定
        mock_transcription_result = MagicMock()
        mock_transcription_result.text = expected_text
        mock_openai_client.audio.transcriptions.create.return_value = mock_transcription_result
        
        # --- Act ---
        # サービスをインスタンス化
        # OpenAIクライアントの初期化をパッチして、モックを返すようにする
        with patch(f"{SERVICE_PATH}.openai.AsyncOpenAI", return_value=mock_openai_client) as mock_constructor, \
             patch("os.path.exists", return_value=True), \
             patch("builtins.open", mock_open(read_data=b"dummy_audio_data")):
            
            service = TranscriptionService(api_key=api_key)
            result_text = await service.transcribe(audio_path, "ja")

        # --- Assert ---
        # OpenAIクライアントが正しいAPIキーで初期化されたか
        mock_constructor.assert_called_once_with(api_key=api_key)
        
        # 文字起こしメソッドが正しい引数で呼び出されたか
        mock_openai_client.audio.transcriptions.create.assert_awaited_once()
        call_args, call_kwargs = mock_openai_client.audio.transcriptions.create.call_args
        assert call_kwargs['model'] == "whisper-1"
        assert call_kwargs['language'] == "ja"
        # file引数はFileObjectなので、ここでは存在することのみを確認
        assert 'file' in call_kwargs
        
        # 戻り値が期待通りか
        assert result_text == expected_text

    @pytest.mark.asyncio
    async def test_transcribe_file_not_found(self):
        """音声ファイルが存在しない場合にFileNotFoundErrorを送出するかテストする。"""
        # --- Arrange ---
        service = TranscriptionService(api_key="dummy_key")
        
        # os.path.exists が False を返すようにパッチ
        with patch("os.path.exists", return_value=False):
            # --- Act & Assert ---
            with pytest.raises(FileNotFoundError, match="Audio file not found at path: /path/to/nonexistent/audio.mp3"):
                await service.transcribe("/path/to/nonexistent/audio.mp3", "ja")
                
    @pytest.mark.asyncio
    async def test_transcribe_api_error_raises_exception(self, mock_openai_client: MagicMock):
        """OpenAI APIがエラーを返した場合に例外が送出されるかテストする。"""
        # --- Arrange ---
        from openai import APIError
        
        api_key = "test_api_key"
        audio_path = "/path/to/fake/audio.mp3"
        
        # API呼び出しがAPIErrorを送出するように設定
        error_response = MagicMock()
        error_response.status_code = 500
        error_response.message = "Internal server error"
        mock_openai_client.audio.transcriptions.create.side_effect = APIError(
            message="Test API Error", request=MagicMock(), body=None
        )
        
        # --- Act & Assert ---
        with patch(f"{SERVICE_PATH}.openai.AsyncOpenAI", return_value=mock_openai_client), \
             patch("os.path.exists", return_value=True), \
             patch("builtins.open", mock_open(read_data=b"dummy_audio_data")):
            
            service = TranscriptionService(api_key=api_key)
            
            # APIErrorがそのまま送出されることを確認
            with pytest.raises(APIError):
                await service.transcribe(audio_path, "ja") 