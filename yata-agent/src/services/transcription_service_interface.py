from abc import ABC, abstractmethod


class TranscriptionServiceInterface(ABC):
    """
    文字起こしサービスのインターフェース。
    """

    @abstractmethod
    async def transcribe(self, audio_file_path: str, language: str) -> str:
        """
        指定された音声ファイルを文字起こしする。

        Args:
            audio_file_path (str): 文字起こし対象の音声ファイルパス。
            language (str): 文字起こしに使用する言語（例: "ja", "en"）。

        Returns:
            str: 文字起こしされたテキスト。

        Raises:
            FileNotFoundError: 音声ファイルが見つからない場合。
            Exception: 文字起こし処理中にエラーが発生した場合。
        """
        pass 