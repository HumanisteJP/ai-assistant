from abc import ABC, abstractmethod
from typing import Dict
from types import SimpleNamespace

class AudioServiceInterface(ABC):
    """Mix per-user audio tracks into a single file and export.

    The recording *sink* from Pycord provides ``audio_data`` mapping
    ``user_id -> SinkAudioData`` where each value exposes a ``file``
    like-object positioned at 0 as well as the original *encoding*.
    """

    @abstractmethod
    async def mix_and_export(
        self,
        sink_audio_data: Dict[int, SimpleNamespace],
        encoding: str,
        out_path: str,
    ) -> str:
        """Combine tracks, ensure minimal duration, write ``out_path``.

        Returns the absolute path of the created file.
        """
        raise NotImplementedError 