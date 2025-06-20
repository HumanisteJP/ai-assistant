import logging

import discord
from discord.ext import commands

from services.readiness_service import ReadinessService, ReadinessLevel
from utils.messages import msg

logger = logging.getLogger(__name__)


class StatusCog(commands.Cog):
    """Provide a self-diagnostic slash command for server admins.

    Checks in order:
    1. `/setup` has been executed (server settings exist)
    2. Google OAuth credentials are present

    The command responds *ephemerally* so only the invoker sees the result.
    """

    def __init__(self, readiness_service: ReadinessService):
        self._readiness_service = readiness_service

    # ------------------------------------------------------------------
    @discord.slash_command(
        name="status",
        description="Yata Bot の自己診断を実行します (管理者専用)",
        default_member_permissions=discord.Permissions(administrator=True),
    )
    async def status(self, ctx: discord.ApplicationContext):  # type: ignore[override]
        """Run diagnostics and report the result as an ephemeral message."""
        await ctx.defer(ephemeral=True)

        if not ctx.guild:
            await ctx.followup.send(content=msg("guild_only"))
            return

        guild_id = ctx.guild.id
        status = self._readiness_service.check(guild_id)

        # Compose response ---------------------------------------------
        lines: list[str] = ["🚦 **Yata Bot Self-Check**"]
        lines.append(
            f"• サーバー設定 (/setup): {'✅ OK' if status.level != ReadinessLevel.NEED_SETUP else '❌ 未設定'}"
        )
        lines.append(
            f"• Google 認証 (/google_auth): {'✅ OK' if status.level == ReadinessLevel.READY else '❌ 未認証'}"
        )

        lines.append(status.guidance())

        await ctx.followup.send(content="\n".join(lines))


# ----------------------------------------------------------------------
# Extension entry-point
# ----------------------------------------------------------------------

def setup(bot: commands.Bot):  # pragma: no cover
    readiness_service = bot.container.readiness_service
    bot.add_cog(StatusCog(readiness_service)) 