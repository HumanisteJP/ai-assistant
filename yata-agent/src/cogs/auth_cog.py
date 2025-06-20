import logging
import discord
from discord.ext import commands

from services.google_service_interface import GoogleServiceInterface
from services.readiness_service import ReadinessLevel
from utils.messages import msg

logger = logging.getLogger(__name__)

class AuthCog(commands.Cog):
    """
    Googleアカウント連携のための認証フローを開始するCog。
    """

    def __init__(self, google_service: GoogleServiceInterface):
        """
        AuthCogのコンストラクタ。

        Args:
            google_service: Google APIとの対話を担当するサービス。
        """
        self.google_service = google_service

    @discord.slash_command(
        name="google_auth",
        description="Googleアカウントと連携し、議事録の保存を許可します。",
    )
    async def google_auth(self, ctx: discord.ApplicationContext):
        """
        Googleの認証URLを生成し、コマンド実行者にDMで送信する。
        """
        await ctx.defer(ephemeral=True)

        if not ctx.guild:
            await ctx.followup.send(msg("guild_only"))
            return

        guild_id = ctx.guild.id

        # ---------------- readiness check ----------------
        try:
            readiness_service = ctx.bot.container.readiness_service  # type: ignore[attr-defined]
            status = readiness_service.check(guild_id)
            if status.level == ReadinessLevel.NEED_SETUP:
                await ctx.followup.send(status.guidance())
                return
        except AttributeError:
            pass

        state = f"gid:{guild_id}"

        try:
            auth_url = await self.google_service.get_authentication_url(state=state)

            # ユーザーにDMで認証URLを送信
            dm_message = (
                f"こんにちは！ **{ctx.guild.name}** サーバーとの連携を続けるには、\n"
                f"以下のリンクをクリックしてGoogleアカウントで認証してください。\n\n"
                f"🔗 **[認証リンク]({auth_url})**\n\n"
                "このリンクはあなた専用です。他人と共有しないでください。"
            )
            await ctx.author.send(dm_message)

            await ctx.followup.send(
                content=msg("auth_url_sent")
            )
            logger.info(f"Sent auth URL to user {ctx.author.id} for guild {guild_id}")

        except Exception as e:
            logger.error(
                f"Failed to get auth URL for guild {guild_id}: {e}", exc_info=True
            )
            await ctx.followup.send("❌ 認証URLの取得に失敗しました。管理者に連絡してください。")

def setup(bot: commands.Bot):
    """Required by bot.load_extension to add the cog."""
    google_service = bot.container.google_service
    bot.add_cog(AuthCog(google_service)) 