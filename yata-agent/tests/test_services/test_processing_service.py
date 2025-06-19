import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from services.processing_service import ProcessingService  # will be created
from services.transcription_service_interface import TranscriptionServiceInterface
from services.google_service_interface import GoogleServiceInterface
from services.database_service import DatabaseService


class TestProcessingService:
    """ProcessingService のビジネスロジックをテストする。"""

    @pytest.fixture
    def mock_transcription_service(self):
        """TranscriptionServiceInterface のモックを返す。"""
        return AsyncMock(spec=TranscriptionServiceInterface)

    @pytest.fixture
    def mock_google_service(self):
        """GoogleServiceInterface のモックを返す。"""
        return AsyncMock(spec=GoogleServiceInterface)

    @pytest.fixture
    def mock_db_service(self):
        """DatabaseService のモックを返す。"""
        return MagicMock(spec=DatabaseService)

    @pytest.mark.asyncio
    async def test_process_success(self, mock_transcription_service, mock_google_service, mock_db_service):
        """音声→議事録→アップロードのフローが正常に完了するケース。"""
        guild_id = 123
        audio_path = "/tmp/audio.wav"
        language = "en"
        transcript_text = "raw transcript"
        formatted_text = "formatted minutes"
        expected_url = "https://docs.google.com/document/d/abc/edit"
        title = "Meeting Minutes"

        # DB から言語設定を返す
        mock_db_service.get_server_settings.return_value = {"language": language}

        # 各サービスの戻り値を設定
        mock_transcription_service.transcribe.return_value = transcript_text
        mock_google_service.upload_document.return_value = expected_url

        # meeting_minutes.format_meeting_minutes をパッチ
        with patch(
            "services.processing_service.format_meeting_minutes", return_value=formatted_text
        ) as mock_formatter:
            service = ProcessingService(
                transcription_service=mock_transcription_service,
                google_service=mock_google_service,
                db_service=mock_db_service,
            )

            result_url = await service.process(
                guild_id=guild_id, audio_file_path=audio_path, title=title
            )

        # 戻り値が期待通りか
        assert result_url == expected_url

        # 呼び出しが正しいか
        mock_db_service.get_server_settings.assert_called_once_with(guild_id)
        mock_transcription_service.transcribe.assert_awaited_once_with(audio_path, language)
        mock_formatter.assert_called_once_with(transcript_text)
        mock_google_service.upload_document.assert_awaited_once_with(
            guild_id, title, formatted_text
        )

    @pytest.mark.asyncio
    async def test_process_formatter_returns_none(self, mock_transcription_service, mock_google_service, mock_db_service):
        """フォーマッタが None を返した場合は元の書き起こしを使用する。"""
        guild_id = 1
        audio_path = "audio.mp3"
        transcript_text = "hello"
        title = "title"
        expected_url = "https://docs"

        mock_db_service.get_server_settings.return_value = None  # デフォルト ja

        mock_transcription_service.transcribe.return_value = transcript_text
        mock_google_service.upload_document.return_value = expected_url

        with patch("services.processing_service.format_meeting_minutes", return_value=None):
            service = ProcessingService(
                transcription_service=mock_transcription_service,
                google_service=mock_google_service,
                db_service=mock_db_service,
            )
            url = await service.process(guild_id, audio_path, title)

        assert url == expected_url
        mock_google_service.upload_document.assert_awaited_once_with(
            guild_id, title, transcript_text
        ) 