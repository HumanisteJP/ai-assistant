import discord
from discord.ext import commands
import os
from dotenv import load_dotenv
from utils.oauth_server import run_oauth_server

# botのインスタンスを作成
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix='!', intents=intents)

# 許可するサーバー（ギルド）のIDを設定
ALLOWED_GUILD_ID = 1061942302534279252  # あなたのサーバーID

# botの起動時刻を記録
bot.uptime = discord.utils.utcnow()

# コマンド実行前のチェック
@bot.check
async def globally_block_dms(ctx):
    # サーバー内でのコマンドかチェック
    if ctx.guild is None:
        return False
    
    # 許可されたサーバーかチェック
    return ctx.guild.id == ALLOWED_GUILD_ID

# メッセージイベントをフィルタリング
@bot.event
async def on_message(message):
    # DMは無視
    if message.guild is None:
        return
    
    # 許可されたサーバーからのメッセージのみ処理
    if message.guild.id == ALLOWED_GUILD_ID:
        await bot.process_commands(message)

# botの準備完了時のイベント
@bot.event
async def on_ready():
    print(f'{bot.user} としてログインしました！')
    
    # 参加しているサーバー情報を表示
    for guild in bot.guilds:
        if guild.id == ALLOWED_GUILD_ID:
            print(f'✅ 許可されたサーバー: {guild.name} (ID: {guild.id})')
        else:
            print(f'❌ 許可されていないサーバー: {guild.name} (ID: {guild.id})')
    
    # スラッシュコマンドを同期
    print('スラッシュコマンドを同期中...')
    try:
        # グローバルにコマンドを同期するが、check関数で許可されたサーバーのみに制限する
        await bot.sync_commands()
        print(f'スラッシュコマンドの同期が完了しました')
    except Exception as e:
        print(f'コマンド同期中にエラーが発生しました: {e}')
    
    print('OAuthサーバーを起動中...')
    try:
        # OAuthサーバーをバックグラウンドで起動
        server_thread = run_oauth_server()
        print(f'OAuthサーバーの起動が完了しました')
    except Exception as e:
        print(f'OAuthサーバー起動中にエラーが発生しました: {e}')
    
    print('------')

# Cogをロード
def load_cogs():
    # cogsディレクトリがなければ作成
    os.makedirs('./cogs', exist_ok=True)
    
    # cogsフォルダのすべてのPythonファイルをロード
    for filename in os.listdir('./cogs'):
        if filename.endswith('.py'):
            try:
                cog_name = f"cogs.{filename[:-3]}"
                bot.load_extension(cog_name)
                print(f'Loaded extension: {cog_name}')
            except Exception as e:
                print(f'Failed to load extension {filename}: {e}')

# botを実行
if __name__ == "__main__":
    # .envファイルから環境変数を読み込む
    load_dotenv()

    # 環境変数からトークンを取得
    TOKEN = os.getenv('DISCORD_TOKEN')

    # Cogをロード
    load_cogs()

    # トークンがない場合のフォールバック（開発環境用）
    if not TOKEN:
        print("警告: 環境変数からトークンが見つかりませんでした。")
        print("環境変数 'DISCORD_TOKEN' を設定するか、.envファイルを作成してください。")
        # 開発用のトークン（本番環境では絶対に使用しないでください）
        TOKEN = 'MTM3Mjk1MDYyNTY3OTE4Mzk4Mw.GrJ8Z9.BAeJfOU-jziTq1qq8HH5fkHSrY_k2NI9o0dfwY'

    bot.run(TOKEN)