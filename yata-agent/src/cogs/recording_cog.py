from __future__ import annotations

import datetime as _dt
import logging
from pathlib import Path
from types import SimpleNamespace
from typing import Dict

import discord
from discord.ext import commands

from services.processing_service import ProcessingService
from services.audio_service import AudioService

logger = logging.getLogger(__name__)

# Temporary recordings storage  
TEMP_DIR = Path("recordings")
TEMP_DIR.mkdir(exist_ok=True)


class RecordingCog(commands.Cog):
    """Discord voice recording and meeting minutes generation."""

    def __init__(self, processing_service: ProcessingService, audio_service: AudioService):
        self.processing_service = processing_service
        self.audio_service = audio_service
        # guild_id -> {voice_client, file_path}
        self._active_recordings: Dict[int, SimpleNamespace] = {}

    # ---------------------------- record start ----------------------------
    @discord.slash_command(name="record_start", description="ボイスチャンネルの録音を開始します。")
    async def record_start(self, ctx: discord.ApplicationContext):  # type: ignore[override]
        await ctx.defer(ephemeral=True)

        voice_state = getattr(ctx.author, "voice", None)
        if not voice_state or not voice_state.channel:
            await ctx.followup.send("❌ 先にボイスチャンネルへ参加してください。")
            return

        guild_id = ctx.guild.id if ctx.guild else 0
        
        if guild_id in self._active_recordings:
            await ctx.followup.send("⚠️ すでに録音中です。/record_stop で停止してください。")
            return

        voice_channel: discord.VoiceChannel = voice_state.channel  # type: ignore[assignment]
        
        try:
            voice_client: discord.VoiceClient = await voice_channel.connect()
        except Exception as e:  # pragma: no cover
            logger.error("Voice connect failed: %s", e, exc_info=True)
            await ctx.followup.send("❌ ボイスチャンネルへの接続に失敗しました。")
            return

        # --------------------- start recording -------------------------
        from discord import sinks

        sink = sinks.WaveSink()
        voice_client.start_recording(sink, self._on_record_finished, ctx.channel)

        self._active_recordings[guild_id] = SimpleNamespace(
            voice_client=voice_client,
            sink=sink,
        )

        await ctx.followup.send("✅ 録音を開始しました。/record_stop で停止します。")

    # ---------------------------- record stop -----------------------------
    @discord.slash_command(name="record_stop", description="録音を停止し、議事録作成を開始します。")
    async def record_stop(self, ctx: discord.ApplicationContext):  # type: ignore[override]
        await ctx.defer(ephemeral=True)
        guild_id = ctx.guild.id if ctx.guild else 0
        record = self._active_recordings.get(guild_id)
        if not record:
            await ctx.followup.send("❌ 現在録音は行われていません。")
            return

        voice_client: discord.VoiceClient = record.voice_client  # type: ignore[attr-defined]
        try:
            voice_client.stop_recording()
            await voice_client.disconnect()
        except Exception:  # pragma: no cover
            logger.warning("Voice disconnect failed", exc_info=True)

        # state cleanup
        self._active_recordings.pop(guild_id, None)

        await ctx.followup.send("⏹️ 録音を停止しました。録音データを処理します…")

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    async def _on_record_finished(self, sink, channel, *args):  # noqa: D401
        """Callback invoked by py-cord when recording is finished."""
        guild_id = channel.guild.id if hasattr(channel, 'guild') and channel.guild else 0

        try:
            # Disconnect from voice channel as per Pycord guide
            if hasattr(sink, 'vc') and sink.vc:
                await sink.vc.disconnect()
            
            if not sink.audio_data:
                await channel.send("⚠️ 録音データがありませんでした。録音中にボイスチャンネルで話されていたか確認してください。")
                return

            # List recorded users
            recorded_users = [
                f"<@{user_id}>"
                for user_id, audio in sink.audio_data.items()
            ]
            
            # Check if we have actual audio content
            total_size = 0
            for user_id, audio in sink.audio_data.items():
                if hasattr(audio, 'file'):
                    audio.file.seek(0, 2)  # Seek to end
                    size = audio.file.tell()
                    audio.file.seek(0)  # Reset to beginning
                    total_size += size
                else:
                    logger.warning(f"User {user_id} audio object has no 'file' attribute")
            
            if total_size == 0:
                await channel.send("⚠️ 録音データが空でした。ボイスチャンネルでの音声が検出されませんでした。")
                return

            await channel.send(f"🎤 録音を検出しました: {', '.join(recorded_users)}. 処理を開始します...")

            # Generate output path
            timestamp = _dt.datetime.now().strftime("%Y%m%d_%H%M%S")
            base_path = TEMP_DIR / f"recording_{guild_id}_{timestamp}"
            
            # Delegate to AudioService (runs in thread) – returns .ogg path
            out_path_str = await self.audio_service.mix_and_export(
                sink.audio_data,
                sink.encoding,
                base_path.as_posix(),
            )

            # Invoke ProcessingService
            title = f"Meeting Minutes {_dt.datetime.now().strftime('%Y-%m-%d %H:%M')}"
            url = await self.processing_service.process(guild_id, out_path_str, title)

            await channel.send(f"✅ 議事録を作成しました: {url}")

        except Exception as exc:  # pragma: no cover
            logger.error("Processing failed: %s", exc, exc_info=True)
            await channel.send("❌ 議事録の作成に失敗しました。")


def setup(bot: commands.Bot):  # pragma: no cover
    """Required by bot.load_extension to add the cog."""
    processing_service = bot.container.processing_service
    audio_service = bot.container.audio_service
    bot.add_cog(RecordingCog(processing_service, audio_service)) 