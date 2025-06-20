import asyncio
import io
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch, MagicMock

import pytest
import sys
from pathlib import Path

# Add src to path for test discovery when running direct file
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

import discord  # py-cord

from cogs.recording_cog import RecordingCog  # will create
from services.processing_service import ProcessingService
from services.audio_service import AudioService
from services.readiness_service import ReadinessService, ReadinessLevel


@pytest.fixture
def mock_processing_service() -> AsyncMock:
    """ProcessingService のモックを返す。"""
    return AsyncMock(spec=ProcessingService)


@pytest.fixture
def mock_audio_service() -> AsyncMock:
    return AsyncMock(spec=AudioService)


@pytest.fixture
def mock_readiness_service() -> MagicMock:
    return MagicMock(spec=ReadinessService)


@pytest.fixture
def recording_cog(mock_processing_service: AsyncMock, mock_audio_service: AsyncMock) -> RecordingCog:
    """テスト対象の RecordingCog を返す。"""
    return RecordingCog(processing_service=mock_processing_service, audio_service=mock_audio_service)


# --- Helper mocks ------------------------------------------------------------

class _MockVoiceState:
    def __init__(self, channel: discord.VoiceChannel | None):
        self.channel = channel


@pytest.mark.asyncio
class TestRecordingCog:
    async def test_record_start_success(self, recording_cog: RecordingCog):
        """/record_start が正常に動作し、VC へ接続される。"""
        # Arrange
        voice_channel = AsyncMock(spec=discord.VoiceChannel)
        voice_client = AsyncMock(spec=discord.VoiceClient)
        voice_client.start_recording = MagicMock()
        voice_channel.connect.return_value = voice_client

        mock_ctx = AsyncMock(spec=discord.ApplicationContext)
        mock_ctx.defer = AsyncMock()
        mock_ctx.followup.send = AsyncMock()
        mock_ctx.author.voice = _MockVoiceState(channel=voice_channel)
        mock_ctx.guild.id = 1

        # Act
        await recording_cog.record_start.callback(recording_cog, mock_ctx)

        # Assert
        voice_channel.connect.assert_awaited_once()
        voice_client.start_recording.assert_called_once()
        mock_ctx.followup.send.assert_awaited_once()
        assert 1 in recording_cog._active_recordings  # type: ignore[attr-defined]

    async def test_record_start_no_voice(self, recording_cog: RecordingCog):
        """VC に接続していない場合にエラーメッセージが返る。"""
        mock_ctx = AsyncMock(spec=discord.ApplicationContext)
        mock_ctx.defer = AsyncMock()
        mock_ctx.followup.send = AsyncMock()
        mock_ctx.author.voice = _MockVoiceState(channel=None)

        await recording_cog.record_start.callback(recording_cog, mock_ctx)

        mock_ctx.followup.send.assert_awaited_once()
        # active_recordings に登録されていない
        assert recording_cog._active_recordings == {}

    async def test_record_stop_success(self, recording_cog: RecordingCog):
        """/record_stop が VC の録音停止と切断を行う。"""
        guild_id = 99

        # active_recordings エントリを模擬
        voice_client = AsyncMock(spec=discord.VoiceClient)
        voice_client.stop_recording = MagicMock()
        recording_cog._active_recordings[guild_id] = SimpleNamespace(  # type: ignore[attr-defined]
            voice_client=voice_client,
            sink=None,
        )

        mock_ctx = AsyncMock(spec=discord.ApplicationContext)
        mock_ctx.defer = AsyncMock()
        mock_ctx.followup.send = AsyncMock()
        mock_ctx.guild.id = guild_id

        await recording_cog.record_stop.callback(recording_cog, mock_ctx)

        mock_ctx.followup.send.assert_awaited_once()
        voice_client.stop_recording.assert_called_once()
        voice_client.disconnect.assert_awaited_once()

    async def test_finished_callback_invokes_processing(self, recording_cog: RecordingCog, mock_processing_service: AsyncMock):
        """録音完了コールバックで ProcessingService.process が呼ばれる"""
        # Arrange
        class DummyAudio:
            def __init__(self):
                self.file = asyncio.StreamReader()  # placeholder

        sink = SimpleNamespace(audio_data={111: SimpleNamespace(file=io.BytesIO(b"\\x00\\x00"))}, encoding="wav")

        mock_ctx = AsyncMock(spec=discord.ApplicationContext)
        mock_ctx.followup.send = AsyncMock()
        mock_ctx.guild.id = 123

        # Patch pydub.AudioSegment to avoid heavy processing
        with patch("pydub.AudioSegment", autospec=True) as mock_segment:
            segment_instance = mock_segment.from_file.return_value
            segment_instance.overlay.return_value = segment_instance
            await recording_cog._on_record_finished(sink, mock_ctx)

        mock_processing_service.process.assert_awaited_once()

    async def test_record_start_blocks_when_not_ready(self, recording_cog: RecordingCog, mock_readiness_service: MagicMock):
        """/record_start should block if readiness not OK"""
        mock_readiness_service.check.return_value.level = ReadinessLevel.NEED_AUTH
        mock_readiness_service.check.return_value.guidance.return_value = "❌"

        ctx = AsyncMock(spec=discord.ApplicationContext)
        ctx.defer = AsyncMock()
        ctx.followup.send = AsyncMock()
        ctx.author.voice = _MockVoiceState(channel=None)  # voice not required for this test
        ctx.guild.id = 1

        # inject container with readiness
        bot = MagicMock()
        container = MagicMock()
        container.readiness_service = mock_readiness_service
        bot.container = container
        ctx.bot = bot

        await recording_cog.record_start.callback(recording_cog, ctx)

        # Should send guidance and not attempt processing
        ctx.followup.send.assert_awaited_once()
        args, kwargs = ctx.followup.send.call_args
        sent = kwargs.get("content", args[0] if args else "")
        assert "❌" in sent
        # ensure no recording state stored
        assert recording_cog._active_recordings == {}

    async def test_record_stop_dm_disallowed(self, recording_cog: RecordingCog):
        """/record_stop DM 実行で guild-only メッセージ"""
        ctx = AsyncMock(spec=discord.ApplicationContext)
        ctx.defer = AsyncMock()
        ctx.followup.send = AsyncMock()
        ctx.guild = None

        await recording_cog.record_stop.callback(recording_cog, ctx)

        ctx.followup.send.assert_awaited_once()
        args, kwargs = ctx.followup.send.call_args
        content = kwargs.get("content", args[0] if args else "")
        assert "サーバー内でのみ実行" in content

    async def test_record_stop_guidance_when_not_ready(self, recording_cog: RecordingCog, mock_readiness_service: MagicMock):
        """未設定状態で /record_stop がガイドを返す"""
        mock_readiness_service.check.return_value.level = ReadinessLevel.NEED_SETUP
        mock_readiness_service.check.return_value.guidance.return_value = "❌"

        ctx = AsyncMock(spec=discord.ApplicationContext)
        ctx.defer = AsyncMock()
        ctx.followup.send = AsyncMock()
        ctx.guild.id = 1

        bot = MagicMock()
        container = MagicMock()
        container.readiness_service = mock_readiness_service
        bot.container = container
        ctx.bot = bot

        await recording_cog.record_stop.callback(recording_cog, ctx)

        ctx.followup.send.assert_awaited_once()
        args, kwargs = ctx.followup.send.call_args
        content = kwargs.get("content", args[0] if args else "")
        assert "❌" in content 