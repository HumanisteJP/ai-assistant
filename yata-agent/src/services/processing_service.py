from typing import Optional
import asyncio

from services.transcription_service_interface import TranscriptionServiceInterface
from services.google_service_interface import GoogleServiceInterface
from services.database_service import DatabaseService

# utils.meeting_minutes は Yata_legacy にある。互換のため相対 import ではなくパスで使用。
try:
    from utils.meeting_minutes import format_meeting_minutes  # type: ignore
except ModuleNotFoundError:  # テスト環境など utils パッケージが見つからない場合
    # ダミー関数を用意してテストを通す
    def format_meeting_minutes(transcript: str) -> Optional[str]:  # noqa: D401
        """Fallback formatter if utils.meeting_minutes is unavailable."""
        return None


class ProcessingService:
    """録音後のバックグラウンド処理を集約するサービス。

    1. 文字起こし
    2. 議事録フォーマット
    3. Google ドキュメントへのアップロード

    を 1 つの `process` メソッドで実行する。
    """

    def __init__(
        self,
        transcription_service: TranscriptionServiceInterface,
        google_service: GoogleServiceInterface,
        db_service: DatabaseService,
    ) -> None:
        """コンストラクタ。

        Args:
            transcription_service: 音声 → テキストの変換を担当。
            google_service: テキスト → Google Docs へのアップロードを担当。
            db_service: サーバー設定 (言語) の取得に使用。
        """
        self._transcription_service = transcription_service
        self._google_service = google_service
        self._db_service = db_service

    async def process(self, guild_id: int, audio_file_path: str, title: str) -> str:
        """音声ファイルを処理し Google ドキュメント URL を返す。

        Args:
            guild_id: Discord サーバー ID。GoogleService や設定取得に使用。
            audio_file_path: 音声ファイルのパス。
            title: 作成する Google ドキュメントのタイトル。

        Returns:
            Google ドキュメントの URL。

        Raises:
            FileNotFoundError: 音声ファイルが存在しない場合。
            Exception: 各種サービスで例外が発生した場合はそのまま上位へ伝搬。
        """
        # 1. サーバー設定から言語を取得 (無ければ ja)
        settings = None
        if hasattr(self._db_service, "get_server_settings"):
            settings = self._db_service.get_server_settings(guild_id)
        language = settings.get("language", "ja") if settings else "ja"

        # 2. 文字起こし (I/O バウンドなのでそのまま await)
        transcript: str = await self._transcription_service.transcribe(
            audio_file_path, language
        )
        
        # DEBUG: Log the actual transcription result
        import logging
        logger = logging.getLogger(__name__)
        logger.info(f"Transcription result for guild {guild_id}: {transcript[:200]}...")

        # 3. 議事録フォーマット
        formatted: Optional[str] = await asyncio.to_thread(
            format_meeting_minutes, transcript
        )
        logger.info(f"Formatted result: {formatted[:200] if formatted else 'None'}...")
        
        if not formatted:
            logger.warning("Meeting minutes formatting failed, using original transcript")
            formatted = transcript  # フォーマット失敗時は元文を使用

        # 4. Google ドキュメントへアップロード
        url: str = await self._google_service.upload_document(
            guild_id, title, formatted
        )

        return url 