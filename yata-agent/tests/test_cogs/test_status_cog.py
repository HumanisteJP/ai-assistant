from unittest.mock import AsyncMock, MagicMock
import sys
from pathlib import Path
import pytest
import discord

# Add src path
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from cogs.status_cog import StatusCog  # noqa: E402
from services.readiness_service import ReadinessService, ReadinessLevel  # noqa: E402


@pytest.fixture
def mock_readiness() -> MagicMock:
    return MagicMock(spec=ReadinessService)


@pytest.fixture
def status_cog(mock_readiness: MagicMock) -> StatusCog:
    return StatusCog(readiness_service=mock_readiness)


@pytest.mark.asyncio
class TestStatusCog:
    async def test_status_all_ok(self, status_cog: StatusCog, mock_readiness: MagicMock):
        # Arrange
        mock_readiness.check.return_value.level = ReadinessLevel.READY
        mock_readiness.check.return_value.guidance.return_value = "✅"

        ctx = AsyncMock(spec=discord.ApplicationContext)
        ctx.defer = AsyncMock()
        ctx.followup.send = AsyncMock()
        ctx.guild.id = 1

        # Act
        await status_cog.status.callback(status_cog, ctx)  # type: ignore[attr-defined]

        # Assert
        ctx.defer.assert_awaited_once_with(ephemeral=True)
        ctx.followup.send.assert_awaited_once()
        sent = ctx.followup.send.call_args.kwargs["content"]
        assert "✅" in sent
        assert "サーバー設定" in sent

    async def test_status_setup_missing(self, status_cog: StatusCog, mock_readiness: MagicMock):
        mock_readiness.check.return_value.level = ReadinessLevel.NEED_SETUP
        mock_readiness.check.return_value.guidance.return_value = "❌"

        ctx = AsyncMock(spec=discord.ApplicationContext)
        ctx.defer = AsyncMock()
        ctx.followup.send = AsyncMock()
        ctx.guild.id = 99

        await status_cog.status.callback(status_cog, ctx)  # type: ignore[attr-defined]

        sent = ctx.followup.send.call_args.kwargs["content"]
        assert "❌" in sent
        assert "/setup" in sent

    async def test_status_dm_disallowed(self, status_cog: StatusCog):
        """/status run in DM should return guild-only bilingual message."""
        ctx = AsyncMock(spec=discord.ApplicationContext)
        ctx.defer = AsyncMock()
        ctx.followup.send = AsyncMock()
        ctx.guild = None

        await status_cog.status.callback(status_cog, ctx)  # type: ignore[attr-defined]

        ctx.followup.send.assert_awaited_once()
        content = ctx.followup.send.call_args.kwargs["content"]
        assert "サーバー内でのみ実行" in content
        assert "This command can only be used" in content 