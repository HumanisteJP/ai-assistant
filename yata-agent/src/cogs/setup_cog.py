import logging

import discord
from discord.commands import Option
from discord.ext import commands

from services.database_service import DatabaseService
from utils.messages import msg

# ロガーの設定
logger = logging.getLogger(__name__)

class SetupCog(commands.Cog):
    """
    サーバー管理者がボットの初期設定を行うためのCog。
    """

    def __init__(self, db_service: DatabaseService):
        """
        SetupCogのコンストラクタ。

        Args:
            db_service (DatabaseService): データベースとのやり取りを行うサービス。
        """
        # 依存性注入 (DI) により、外部からDatabaseServiceのインスタンスを受け取る
        self.db_service = db_service

    @discord.slash_command(
        name="setup",
        description="このサーバーのボット設定を行います。管理者のみが実行できます。",
        default_member_permissions=discord.Permissions(administrator=True)
    )
    async def setup(
        self,
        ctx: discord.ApplicationContext,
        gdrive_folder_id: str | None = Option(
            str,
            description="議事録を保存するGoogle DriveのフォルダID（未入力の場合は My Drive 直下に保存されます）",
            required=False,
            default=None,
        ),  # type: ignore[arg-type]
        language: str = Option(
            str,
            description="文字起こしに使用する言語",
            choices=["ja", "en"],
            default="ja",
        ),  # type: ignore[arg-type]
    ):
        """
        サーバーの設定をデータベースに保存するSlash Command。
        """
        # ephemeral=True を指定すると、コマンド実行者のみにメッセージが見える
        # defer()で応答を保留し、時間のかかる処理に備える
        await ctx.defer(ephemeral=True)

        if not ctx.guild:
            await ctx.followup.send(content=msg("guild_only"))
            return

        guild_id = ctx.guild.id
        owner_id = ctx.author.id

        # デフォルト（None または空文字列）の場合は Google Drive のルート ID "root" を使用
        folder_id = gdrive_folder_id or "root"

        try:
            # 依存しているサービスを呼び出して、ビジネスロジックを実行
            self.db_service.upsert_server_settings(
                guild_id=guild_id,
                owner_id=owner_id,
                gdrive_folder_id=folder_id,
                language=language
            )
            
            # 成功メッセージを送信
            location_note = "(My Drive 直下)" if folder_id == "root" else ""

            success_message = (
                "✅ サーバー設定を保存しました。\n"
                f"・Google DriveフォルダID: `{folder_id}` {location_note}\n"
                f"・文字起こし言語: `{language}`"
            )
            await ctx.followup.send(content=success_message)
            logger.info(
                f"Server settings saved for guild {guild_id} by user {owner_id}. folder_id={folder_id}"
            )

        except Exception as e:
            # エラーが発生した場合は、ユーザーにエラーを通知し、ログを記録
            logger.error(f"Failed to save settings for guild {guild_id}: {e}", exc_info=True)
            error_message = (
                "❌ エラーが発生しました。\n"
                "設定の保存に失敗しました。ボットの管理者に連絡してください。"
            )
            await ctx.followup.send(content=error_message)

def setup(bot: commands.Bot):
    """Setup function required by `bot.load_extension`."""
    db_service = bot.container.db_service
    bot.add_cog(SetupCog(db_service))
