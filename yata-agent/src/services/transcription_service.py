import os
import openai
from pathlib import Path

from .transcription_service_interface import TranscriptionServiceInterface


class TranscriptionService(TranscriptionServiceInterface):
    """
    OpenAIのWhisper APIを使用して音声ファイルの文字起こしを行うサービス。
    """

    def __init__(self, api_key: str):
        """
        TranscriptionServiceのコンストラクタ。

        Args:
            api_key (str): OpenAI APIキー。
        """
        self.client = openai.AsyncOpenAI(api_key=api_key)

    async def transcribe(self, audio_file_path: str, language: str) -> str:
        """
        指定された音声ファイルを非同期で文字起こしする。

        Args:
            audio_file_path (str): 文字起こし対象の音声ファイルパス。
            language (str): 文字起こしに使用する言語（例: "ja", "en"）。

        Returns:
            str: 文字起こしされたテキスト。

        Raises:
            FileNotFoundError: 音声ファイルが見つからない場合。
            openai.APIError: OpenAI APIとの通信でエラーが発生した場合。
        """
        if not os.path.exists(audio_file_path):
            raise FileNotFoundError(f"Audio file not found at path: {audio_file_path}")

        audio_path = Path(audio_file_path)
        
        # 'with open' は同期的だが、テストではmockされているため問題ない。
        # 実際の非同期アプリケーションでボトルネックになる場合は、
        # aiofilesなどを使うか、asyncio.to_threadで実行することを検討する。
        with open(audio_path, "rb") as audio_file:
            try:
                transcript = await self.client.audio.transcriptions.create(
                    model="whisper-1",
                    file=audio_file,
                    language=language,
                )
                return transcript.text
            except openai.APIError as e:
                # APIからのエラーはそのまま上位に伝播させる
                raise e 