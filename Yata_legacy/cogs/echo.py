from discord.ext import commands
import asyncio
import sys
import os
from pathlib import Path
import pickle
import time
import discord

# 親ディレクトリをパスに追加してimportできるようにする
sys.path.append(str(Path(__file__).parent.parent))
from utils.google_docs_utils import get_credentials, SCOPES, check_credentials
from utils.oauth_server import get_auth_url
from google_auth_oauthlib.flow import InstalledAppFlow
from google.genai import types
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService

class EchoCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.session_service = InMemorySessionService()
        # 処理中のメッセージを追跡
        self.processing_messages = {}  # {message_id: placeholder_message}
        print("EchoCog が初期化されました")

    @commands.Cog.listener()
    async def on_message(self, message):
        # 自分のメッセージには反応しない
        if message.author == self.bot.user:
            return
        
        # 認証コードを処理する場合
        if message.content.startswith("認証コード:"):
            await self.process_auth_code(message)
            return
        
        # DMには反応しない
        if message.guild is None:
            return
            
        # ボットがメンションされているか確認
        if self.bot.user.mentioned_in(message):
            # @everyoneや@hereの特殊メンションがある場合は反応しない
            if message.mention_everyone:
                return
                
            # メンションを除去したメッセージ内容を取得
            content = message.content
            
            # 全てのメンションを削除
            for mention in message.mentions:
                content = content.replace(f'<@{mention.id}>', '')
                content = content.replace(f'<@!{mention.id}>', '')
            
            # 空白を整理
            content = content.strip()
            
            # 内容が空でなければ処理
            if content:
                await self.process_agent_request(message, content)
            else:
                await message.reply("何かお手伝いできることはありますか？", mention_author=False)
    
    async def process_auth_code(self, message):
        """認証コードを処理する関数"""
        try:
            # 処理中メッセージを送信
            processing_msg = await message.reply("認証コードを処理中...", mention_author=False)
            
            # コードを抽出
            auth_code = message.content.replace("認証コード:", "").strip()
            guild_id = str(message.guild.id)
            
            # 認証フローを作成
            flow = InstalledAppFlow.from_client_secrets_file(
                'credentials.json',
                SCOPES
            )
            
            # 認証コードを使用してトークンを取得
            flow.fetch_token(code=auth_code)
            creds = flow.credentials
            
            # トークンを保存
            token_file = f'token_{guild_id}.pickle'
            with open(token_file, 'wb') as token:
                pickle.dump(creds, token)
            
            await processing_msg.edit(content="✅ 認証が完了しました。Google DriveとDocsにアクセスできるようになりました。\nボットにメンションして質問すると、エージェントが回答します。")
        except Exception as e:
            error_msg = f"認証プロセス中にエラーが発生しました: {str(e)}"
            print(error_msg)
            await message.reply(f"❌ {error_msg}\n正しい認証コードを入力してください。", mention_author=False)
    
    async def process_agent_request(self, message, content):
        """エージェントリクエストを処理する関数"""
        # 考え中メッセージを送信
        placeholder = await message.reply("考え中...", mention_author=False)
        self.processing_messages[message.id] = placeholder
        
        start_time = time.time()
        
        # Google認証の確認
        guild_id = str(message.guild.id)
        creds, need_auth = get_credentials(guild_id)
        
        if need_auth:
            # 認証が必要な場合
            await self.handle_auth_required(placeholder, guild_id)
            return
        
        # ADKエージェントを呼び出す
        try:
            # エージェントのインポート
            sys.path.append(str(Path(__file__).parent.parent / "agents"))
            from agents import root_agent
            
            # セッションの作成または取得
            session = self.session_service.create_session(
                state={}, 
                app_name='Yata', 
                user_id=str(message.author.id)
            )
            
            # Runnerの作成
            runner = Runner(
                app_name='Yata',
                agent=root_agent,
                session_service=self.session_service
            )
            
            # コンテンツの作成
            agent_content = types.Content(role='user', parts=[types.Part(text=content)])
            
            # 3秒ごとに「考え中...」メッセージを更新するタスク
            thinking_task = asyncio.create_task(self.update_thinking_message(placeholder))
            
            try:
                # エージェントの実行（非同期）
                result = await self.run_agent_async(runner, session.id, str(message.author.id), agent_content)
                
                # プレースホルダーを更新
                await placeholder.edit(content=result)
            finally:
                # タスクをキャンセル
                thinking_task.cancel()
                
                # 処理中メッセージから削除
                if message.id in self.processing_messages:
                    del self.processing_messages[message.id]
            
        except Exception as e:
            error_msg = f"エージェントの実行中にエラーが発生しました: {str(e)}"
            print(error_msg)
            
            # プレースホルダーが存在する場合は更新
            if message.id in self.processing_messages and self.processing_messages[message.id].id == placeholder.id:
                await placeholder.edit(content=f"❌ {error_msg}")
                
                # 処理中メッセージから削除
                del self.processing_messages[message.id]
    
    async def handle_auth_required(self, placeholder, guild_id):
        """認証が必要な場合の処理"""
        auth_message = "⚠️ Google DriveとDocsへのアクセスには認証が必要です。"
        
        try:
            # 認証URLを取得
            auth_url = get_auth_url(guild_id)
            
            if auth_url:
                instructions = "以下のURLにアクセスして認証を行ってください。\n認証後、表示されるコードをコピーして「認証コード: [コード]」の形式で返信してください。"
                await placeholder.edit(content=f"{auth_message}\n\n{instructions}\n\n{auth_url}")
            else:
                await placeholder.edit(content=f"{auth_message}\n\n認証URLの取得に失敗しました。管理者に連絡してください。")
        except Exception as e:
            error_msg = f"認証プロセスの開始中にエラーが発生しました: {str(e)}"
            print(error_msg)
            await placeholder.edit(content=f"❌ {error_msg}")
    
    async def update_thinking_message(self, message):
        """「考え中...」メッセージを定期的に更新する関数"""
        thinking_patterns = [
            "考え中...",
            "考え中.",
            "考え中..",
            "考え中..."
        ]
        
        i = 0
        try:
            while True:
                pattern = thinking_patterns[i % len(thinking_patterns)]
                await message.edit(content=pattern)
                await asyncio.sleep(1.5)
                i += 1
        except asyncio.CancelledError:
            # タスクがキャンセルされた場合は何もしない
            pass
        except Exception as e:
            print(f"思考メッセージの更新中にエラーが発生しました: {e}")
    
    async def run_agent_async(self, runner, session_id, user_id, content):
        """エージェントを実行し、最終的な応答を取得する関数"""
        events_async = runner.run_async(
            session_id=session_id,
            user_id=user_id,
            new_message=content
        )
        
        final_response = "エージェントからの応答を取得できませんでした。"
        
        async for event in events_async:
            if event.is_final_response():
                if event.content and event.content.parts:
                    final_response = event.content.parts[0].text
                break
        
        return final_response
    
def setup(bot):
    bot.add_cog(EchoCog(bot)) 