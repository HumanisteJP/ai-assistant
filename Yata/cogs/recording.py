import discord
from discord.ext import commands
import io
import os
import tempfile
from pydub import AudioSegment
import datetime
import time
import pathlib
import asyncio
from discord.commands import Option
from utils.audio_transcription import transcribe_audio
from utils.google_docs_utils import save_to_google_docs, check_credentials
from utils.meeting_minutes import format_meeting_minutes
from utils.oauth_server import get_auth_url

class RecordingCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        # 録音の開始時間を保存するための辞書
        self.recording_start_times = {}
        # 現在録音中のサーバーとチャンネルを追跡
        self.recording_servers = {}  # {guild_id: channel_id} 形式
        # 録音タイマーの辞書
        self.recording_timers = {}  # {guild_id: task} 形式
        # 録音の保存先ディレクトリ
        self.RECORDINGS_DIR = os.getenv('RECORDINGS_DIR', './recordings')
        # Google Docsの保存先フォルダID
        self.GOOGLE_DOCS_FOLDER_ID = "1r-SotVQe0Gxy6H6vdJ8Vr_CRXglxXR3D"
        # 録音保存用ディレクトリを作成
        os.makedirs(self.RECORDINGS_DIR, exist_ok=True)
        print(f'録音の保存先: {os.path.abspath(self.RECORDINGS_DIR)}')

    @commands.slash_command(description="録音を開始します。")
    async def record_start(
        self, 
        ctx, 
        channel= Option(discord.VoiceChannel, "録音するボイスチャンネル", required=False)
    ):
        # 初期メッセージを送信
        initial_message = await ctx.respond(f"録音開始\nボイスチャンネルに接続中...", ephemeral=False)
        message = await initial_message.original_response()
        
        # Google Docsの認証情報をチェック
        is_authenticated = check_credentials(str(ctx.guild.id))
        
        if not is_authenticated:
            # 認証URLを取得
            auth_url = get_auth_url(str(ctx.guild.id))
            if auth_url:
                await message.edit(content=f"⚠️ Google Docsへのアクセス権限がありません。\n\n録音を開始する前に以下のURLをクリックして認証を行ってください：\n{auth_url}\n\n認証完了後、`/auth_check`コマンドで認証状態を確認してから再度お試しください。")
                return
            else:
                await message.edit(content=f"⚠️ Google Docsへのアクセス権限がありませんが、認証URLの取得に失敗しました。\n管理者に連絡してください。")
                return
        
        # 同じサーバー内で既に録音中かチェック
        if ctx.guild.id in self.recording_servers:
            current_channel_id = self.recording_servers[ctx.guild.id]
            try:
                current_channel = self.bot.get_channel(current_channel_id)
                channel_name = current_channel.name if current_channel else "不明なチャンネル"
                await message.edit(content=f"録音開始\nエラー: このサーバーでは既に「{channel_name}」で録音中です。\n録音を停止してから再度お試しください。")
                return
            except Exception as e:
                print(f"チャンネル情報の取得中にエラーが発生しました: {e}")
                await message.edit(content=f"録音開始\nエラー: このサーバーでは既に別のチャンネルで録音中です。\n録音を停止してから再度お試しください。")
                return
        
        # チャンネル指定の優先順位
        # 1. コマンドでチャンネルが指定された場合はそれを使用
        # 2. ユーザーがボイスチャンネルに参加している場合はそのチャンネルを使用
        # 3. どちらも該当しない場合はエラー
        
        target_channel = None
        
        if channel is not None:
            # 指定されたチャンネルを使用
            target_channel = channel
            await message.edit(content=f"録音開始\n指定されたチャンネル「{target_channel.name}」に接続します...")
        elif ctx.author.voice is not None:
            # ユーザーが参加しているチャンネルを使用
            target_channel = ctx.author.voice.channel
            await message.edit(content=f"録音開始\nあなたが参加しているチャンネル「{target_channel.name}」に接続します...")
        else:
            # どちらも該当しない場合はエラー
            await message.edit(content=f"録音開始\nエラー: ボイスチャンネルを指定するか、ボイスチャンネルに参加してください。")
            return
        
        # ボイスチャンネルに接続
        try:
            await target_channel.connect()
        except Exception as e:
            print(f"ボイスチャンネル接続中にエラーが発生しました: {e}")
            await message.edit(content=f"録音開始\nエラー: ボイスチャンネルに接続できません。\nボイスチャンネルの権限を確認してください。")
            return
        
        await message.edit(content=f"録音開始\nボイスチャンネル「{target_channel.name}」に接続しました。")
        
        if ctx.guild.voice_client is None:
            await message.edit(content=f"録音開始\nエラー: ボイスチャンネルに接続していません。")
            return
        
        # ボイスチャンネル接続後に設定
        ctx.voice_client._mix = True
        ctx.voice_client._format = "MP3"
        fromat_sink=discord.sinks.MP3Sink()

        # 録音中のチャンネルとサーバーを記録
        self.recording_servers[ctx.guild.id] = target_channel.id
        
        # 録音開始時間を記録
        self.recording_start_times[ctx.guild.id] = time.time()
        ctx.voice_client.start_recording(fromat_sink, self.finished_callback, ctx)
        
        # 1時間後に自動的に録音を停止するタイマーを設定
        timer_task = asyncio.create_task(self.auto_stop_recording(ctx, target_channel.name))
        self.recording_timers[ctx.guild.id] = timer_task
        
        await message.edit(content=f"録音開始\n✅ ボイスチャンネル「{target_channel.name}」の録音を開始しました。\n⏱️ 1時間後に自動的に録音が終了します。")

    @commands.slash_command(description="録音を停止します。")
    async def record_stop(self, ctx):
        # 初期メッセージを送信
        initial_message = await ctx.respond(f"録音停止\n処理中...", ephemeral=False)
        message = await initial_message.original_response()
        
        # 録音停止処理
        if ctx.guild.voice_client is None:
            await message.edit(content=f"録音停止\nエラー: ボイスチャンネルに接続していません。")
            return
        
        ctx.voice_client.stop_recording()
        await message.edit(content=f"録音停止\n✅ ボイスチャンネルの録音を停止しました。\nボイスチャンネルから切断中...")
        
        # タイマーをキャンセル
        if ctx.guild.id in self.recording_timers:
            self.recording_timers[ctx.guild.id].cancel()
            del self.recording_timers[ctx.guild.id]
        
        # ボイスチャンネルから切断
        if ctx.guild.voice_client is None:
            await message.edit(content=f"録音停止\nエラー: ボイスチャンネルに接続していません。")
            return
        
        await ctx.guild.voice_client.disconnect()
        
        # 録音中のサーバー情報から削除
        if ctx.guild.id in self.recording_servers:
            del self.recording_servers[ctx.guild.id]
        
        await message.edit(content=f"録音停止\n✅ ボイスチャンネルの録音を停止しました。\n✅ ボイスチャンネルから切断しました。")

    async def auto_stop_recording(self, ctx, channel_name):
        """1時間後に自動的に録音を停止する関数"""
        try:
            # 1時間（3600秒）待機
            await asyncio.sleep(3600)
            
            # 録音が既に停止されていないか確認
            if ctx.guild.id not in self.recording_servers:
                return
                
            # 録音停止処理
            if ctx.guild.voice_client and ctx.voice_client:
                ctx.voice_client.stop_recording()
                
                # ボイスチャンネルから切断
                await ctx.guild.voice_client.disconnect()
                
                # 録音中のサーバー情報から削除
                if ctx.guild.id in self.recording_servers:
                    del self.recording_servers[ctx.guild.id]
                    
                # タイマー情報を削除
                if ctx.guild.id in self.recording_timers:
                    del self.recording_timers[ctx.guild.id]
                
                # 通知メッセージを送信
                try:
                    await ctx.channel.send(f"⏱️ 録音時間が1時間に達したため、ボイスチャンネル「{channel_name}」の録音を自動的に停止しました。")
                except Exception as e:
                    print(f"自動録音停止の通知メッセージ送信中にエラーが発生しました: {e}")
        except asyncio.CancelledError:
            # タイマーがキャンセルされた場合（手動で録音停止した場合など）
            pass
        except Exception as e:
            print(f"自動録音停止処理中にエラーが発生しました: {e}")
            try:
                await ctx.channel.send(f"⚠️ 自動録音停止処理中にエラーが発生しました: {e}")
            except:
                pass

    @commands.command(name='record_start', description='ボイスチャンネルの録音を開始します')
    async def record_start_test(
        self,
        ctx,
        channel_id: str = None  # チャンネルIDを文字列として受け取る
    ):
        # 初期メッセージを送信
        message = await ctx.send(f"録音開始\nボイスチャンネルに接続中...")
        
        # Google Docsの認証情報をチェック
        is_authenticated = check_credentials(str(ctx.guild.id))
        
        if not is_authenticated:
            # 認証URLを取得
            auth_url = get_auth_url(str(ctx.guild.id))
            if auth_url:
                await message.edit(content=f"⚠️ Google Docsへのアクセス権限がありません。\n\n録音を開始する前に以下のURLをクリックして認証を行ってください：\n{auth_url}\n\n認証完了後、`!auth_check`コマンドで認証状態を確認してから再度お試しください。")
                return
            else:
                await message.edit(content=f"⚠️ Google Docsへのアクセス権限がありませんが、認証URLの取得に失敗しました。\n管理者に連絡してください。")
                return
        
        # 同じサーバー内で既に録音中かチェック
        if ctx.guild.id in self.recording_servers:
            current_channel_id = self.recording_servers[ctx.guild.id]
            try:
                current_channel = self.bot.get_channel(current_channel_id)
                channel_name = current_channel.name if current_channel else "不明なチャンネル"
                await message.edit(content=f"録音開始\nエラー: このサーバーでは既に「{channel_name}」で録音中です。\n録音を停止してから再度お試しください。")
                return
            except Exception as e:
                print(f"チャンネル情報の取得中にエラーが発生しました: {e}")
                await message.edit(content=f"録音開始\nエラー: このサーバーでは既に別のチャンネルで録音中です。\n録音を停止してから再度お試しください。")
                return
        
        # チャンネル指定の優先順位
        # 1. コマンドでチャンネルIDが指定された場合はそれを使用
        # 2. ユーザーがボイスチャンネルに参加している場合はそのチャンネルを使用
        # 3. どちらも該当しない場合はエラー
        
        target_channel = None
        
        if channel_id is not None:
            # 指定されたチャンネルIDからチャンネルを取得
            try:
                channel_id_int = int(channel_id)
                target_channel = self.bot.get_channel(channel_id_int)
                if target_channel is None or not isinstance(target_channel, discord.VoiceChannel):
                    await message.edit(content=f"録音開始\nエラー: 指定されたIDのボイスチャンネルが見つかりません。")
                    return
                await message.edit(content=f"録音開始\n指定されたチャンネル「{target_channel.name}」に接続します...")
            except ValueError:
                await message.edit(content=f"録音開始\nエラー: チャンネルIDが正しくありません。数字のみを入力してください。")
                return
        elif ctx.author.voice is not None:
            # ユーザーが参加しているチャンネルを使用
            target_channel = ctx.author.voice.channel
            await message.edit(content=f"録音開始\nあなたが参加しているチャンネル「{target_channel.name}」に接続します...")
        else:
            # どちらも該当しない場合はエラー
            await message.edit(content=f"録音開始\nエラー: ボイスチャンネルIDを指定するか、ボイスチャンネルに参加してください。")
            return
        
        # ボイスチャンネルに接続
        try:
            await target_channel.connect()
        except Exception as e:
            print(f"ボイスチャンネル接続中にエラーが発生しました: {e}")
            await message.edit(content=f"録音開始\nエラー: ボイスチャンネルに接続できません。\nボイスチャンネルの権限を確認してください。")
            return
        
        await message.edit(content=f"録音開始\nボイスチャンネル「{target_channel.name}」に接続しました。")
        
        if ctx.guild.voice_client is None:
            await message.edit(content=f"録音開始\nエラー: ボイスチャンネルに接続していません。")
            return
        
        # ボイスチャンネル接続後に設定
        ctx.voice_client._mix = True
        ctx.voice_client._format = "MP3"
        fromat_sink=discord.sinks.MP3Sink()

        # 録音中のチャンネルとサーバーを記録
        self.recording_servers[ctx.guild.id] = target_channel.id
        
        # 録音開始時間を記録
        self.recording_start_times[ctx.guild.id] = time.time()
        ctx.voice_client.start_recording(fromat_sink, self.finished_callback, ctx)
        
        # 1時間後に自動的に録音を停止するタイマーを設定
        timer_task = asyncio.create_task(self.auto_stop_recording(ctx, target_channel.name))
        self.recording_timers[ctx.guild.id] = timer_task
        
        await message.edit(content=f"録音開始\n✅ ボイスチャンネル「{target_channel.name}」の録音を開始しました。\n⏱️ 1時間後に自動的に録音が終了します。")

    @commands.command(name='record_stop', description='ボイスチャンネルの録音を停止します')
    async def record_stop_test(self, ctx):
        # 初期メッセージを送信
        message = await ctx.send(f"録音停止\n処理中...")
        
        # 録音停止処理
        if ctx.guild.voice_client is None:
            await message.edit(content=f"録音停止\nエラー: ボイスチャンネルに接続していません。")
            return
        
        ctx.voice_client.stop_recording()
        await message.edit(content=f"録音停止\n✅ ボイスチャンネルの録音を停止しました。\nボイスチャンネルから切断中...")
        
        # タイマーをキャンセル
        if ctx.guild.id in self.recording_timers:
            self.recording_timers[ctx.guild.id].cancel()
            del self.recording_timers[ctx.guild.id]
        
        # ボイスチャンネルから切断
        if ctx.guild.voice_client is None:
            await message.edit(content=f"録音停止\nエラー: ボイスチャンネルに接続していません。")
            return
        
        await ctx.guild.voice_client.disconnect()
        
        # 録音中のサーバー情報から削除
        if ctx.guild.id in self.recording_servers:
            del self.recording_servers[ctx.guild.id]
        
        await message.edit(content=f"録音停止\n✅ ボイスチャンネルの録音を停止しました。\n✅ ボイスチャンネルから切断しました。")

    @commands.slash_command(description="Google Docsの認証状態を確認します。")
    async def auth_check(self, ctx):
        """Google Docsの認証状態を確認するコマンド"""
        # 初期メッセージを送信
        initial_message = await ctx.respond("認証状態を確認中...", ephemeral=False)
        message = await initial_message.original_response()
        
        # 認証状態を確認
        is_authenticated = check_credentials(str(ctx.guild.id))
        
        if is_authenticated:
            await message.edit(content="✅ Google Docsの認証は有効です。\n録音機能を使用して議事録を作成できます。")
        else:
            # 認証が必要な場合、認証URLを取得
            auth_url = get_auth_url(str(ctx.guild.id))
            if auth_url:
                await message.edit(content=f"❌ Google Docsの認証が必要です。\n\n以下のURLをクリックして認証を行ってください：\n{auth_url}\n\n認証完了後、もう一度このコマンドで認証状態を確認できます。")
            else:
                await message.edit(content="❌ Google Docsの認証が必要ですが、認証URLの取得に失敗しました。\n管理者に連絡してください。")
    
    @commands.command(name='auth_check', description='Google Docsの認証状態を確認します')
    async def auth_check_test(self, ctx):
        """Google Docsの認証状態を確認するテキストコマンド"""
        # メッセージを送信
        message = await ctx.send("認証状態を確認中...")
        
        # 認証状態を確認
        is_authenticated = check_credentials(str(ctx.guild.id))
        
        if is_authenticated:
            await message.edit(content="✅ Google Docsの認証は有効です。\n録音機能を使用して議事録を作成できます。")
        else:
            # 認証が必要な場合、認証URLを取得
            auth_url = get_auth_url(str(ctx.guild.id))
            if auth_url:
                await message.edit(content=f"❌ Google Docsの認証が必要です。\n\n以下のURLをクリックして認証を行ってください：\n{auth_url}\n\n認証完了後、もう一度このコマンドで認証状態を確認できます。")
            else:
                await message.edit(content="❌ Google Docsの認証が必要ですが、認証URLの取得に失敗しました。\n管理者に連絡してください。")

    async def finished_callback(self, sink, ctx, *args):
        recorded_users = [f"<@{user_id}>" for user_id, audio in sink.audio_data.items()]
        files = []
        
        # 録音時間を計算
        try:
            duration_seconds = time.time() - self.recording_start_times.get(ctx.guild.id, time.time())
            minutes, seconds = divmod(int(duration_seconds), 60)
            hours, minutes = divmod(int(minutes), 60)
            duration_str = f"{int(hours):02d}:{int(minutes):02d}:{int(seconds):02d}"
        except Exception as e:
            print(f"録音時間の計算中にエラーが発生しました: {e}")
            duration_str = "不明"
            duration_seconds = 0
        
        # 保存するファイル名のベース（日時とサーバー名）
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        # 年_月_日形式の日付を作成（Google Docsのファイル名用）
        year = datetime.datetime.now().strftime("%Y")
        month = datetime.datetime.now().strftime("%m")
        day = datetime.datetime.now().strftime("%d")
        today = f"{year}_{month}_{day}"
        # 時間と分を取得
        hour = datetime.datetime.now().strftime("%H")
        minute = datetime.datetime.now().strftime("%M")
        server_name = ctx.guild.name.replace(' ', '_').replace('/', '_').replace('\\', '_')
        base_filename = f"{timestamp}_{server_name}"
        
        # チャンネル情報を取得
        try:
            channel_name = ctx.author.voice.channel.name if ctx.author.voice else "不明"
            channel_id = str(ctx.author.voice.channel.id) if ctx.author.voice else "不明"
        except Exception as e:
            print(f"チャンネル情報の取得中にエラーが発生しました: {e}")
            channel_name = "不明"
            channel_id = "不明"
        
        recording_info = {
            'date': datetime.datetime.now().strftime("%Y-%m-%d %H:%M"),
            'duration': duration_str,
            'users': list(sink.audio_data.keys()),
            'channel_name': channel_name,
            'channel_id': channel_id,
            'local_path': None  # ここに後でパスを入れる
        }
        
        # 録音開始時間を削除
        guild_id = ctx.guild.id
        if guild_id in self.recording_start_times:
            del self.recording_start_times[guild_id]
        
        # 録音中のサーバー情報から削除
        if guild_id in self.recording_servers:
            del self.recording_servers[guild_id]
        
        local_path = None
        transcribed_text = None
        
        if len(sink.audio_data) > 0:
            # 音声ファイルをミックスする
            mixed_audio = None
            format = getattr(ctx.voice_client, "_format", "MP3").lower()
            
            # 処理メッセージを送信（統合したメッセージ）
            processing_msg = await ctx.channel.send("音声の圧縮を開始しました。")
            
            # サーバーごとに一意の一時ディレクトリ名を作成
            unique_temp_dir = f"discord_recording_{guild_id}_{timestamp}"
            temp_dir_path = os.path.join(tempfile.gettempdir(), unique_temp_dir)
            
            try:
                # 一時ディレクトリを作成
                os.makedirs(temp_dir_path, exist_ok=True)
                temp_files = []
                
                # 各ユーザーの音声を一時ファイルに保存
                for user_id, audio in sink.audio_data.items():
                    temp_path = os.path.join(temp_dir_path, f"{user_id}.{sink.encoding}")
                    with open(temp_path, 'wb') as f:
                        audio.file.seek(0)
                        f.write(audio.file.read())
                    temp_files.append(temp_path)
                
                # 圧縮中メッセージに更新
                await processing_msg.edit(content="音声の圧縮中です。")
                
                try:
                    # 最初のファイルを基準に使用
                    if temp_files:
                        try:
                            mixed_audio = AudioSegment.from_file(temp_files[0], format=format)
                            
                            # 残りのファイルをオーバーレイ
                            for temp_file in temp_files[1:]:
                                try:
                                    audio_segment = AudioSegment.from_file(temp_file, format=format)
                                    mixed_audio = mixed_audio.overlay(audio_segment)
                                except Exception as e:
                                    print(f"音声ファイルのオーバーレイ中にエラーが発生しました: {e}")
                        except IndexError as e:
                            print(f"音声ファイル処理中にエラーが発生しました: {e}")
                        except Exception as e:
                            print(f"音声ファイルの読み込み中にエラーが発生しました: {e}")
                except Exception as e:
                    print(f"音声ミックス処理中にエラーが発生しました: {e}")
                
                # ミックスした音声をメモリに出力
                if mixed_audio:
                    try:
                        # ローカルに保存
                        local_filename = f"{base_filename}.{format}"
                        local_path = os.path.join(self.RECORDINGS_DIR, local_filename)
                        mixed_audio.export(local_path, format=format)
                        recording_info['local_path'] = local_path
                        
                        # 圧縮完了・文字起こし開始メッセージに更新
                        await processing_msg.edit(content="音声の圧縮が完了しました。文字起こしを実行中です...")
                        
                        # 文字起こし処理を実行
                        try:
                            # 既に文字起こし開始メッセージは更新済み
                            
                            # 文字起こし実行
                            transcribed_text = transcribe_audio(local_path)
                            
                            if transcribed_text:
                                # 文字起こしテキストを議事録形式に変換
                                minutes_text = format_meeting_minutes(transcribed_text)
                                
                                if minutes_text:
                                    # Google Docsの認証情報をチェック
                                    is_authenticated = check_credentials(str(guild_id))
                                    
                                    if not is_authenticated:
                                        # 認証URLを取得
                                        auth_url = get_auth_url(str(guild_id))
                                        if auth_url:
                                            await processing_msg.edit(content=f"✅ 文字起こしと議事録化が完了しました。\n\n⚠️ Google Docsへの保存には認証が必要です。\n以下のURLをクリックして認証を行ってください：\n{auth_url}\n\n認証完了後、`!auth_check`コマンドで認証状態を確認できます。")
                                        else:
                                            await processing_msg.edit(content="✅ 文字起こしと議事録化が完了しました。\n\n⚠️ Google Docsへの保存には認証が必要ですが、認証URLの取得に失敗しました。\n管理者に連絡してください。")
                                        return
                                    
                                    # 認証済みの場合、Google Docsに保存
                                    doc_title = f"{today}_{hour}_{minute}"
                                    doc_url = save_to_google_docs(minutes_text, doc_title, str(guild_id), self.GOOGLE_DOCS_FOLDER_ID)
                                    
                                    if doc_url:
                                        await processing_msg.edit(content=f"✅ 文字起こしと議事録化が完了！\nGoogle Docsに保存しました: [{doc_title}]({doc_url})")
                                    else:
                                        # 保存に失敗した場合も認証切れの可能性があるため、認証URLを表示
                                        auth_url = get_auth_url(str(guild_id))
                                        if auth_url:
                                            await processing_msg.edit(content=f"✅ 文字起こしと議事録化は完了しましたが、\n❌ Google Docsへの保存に失敗しました。\n\n認証が切れている可能性があります。以下のURLから再認証してください：\n{auth_url}")
                                        else:
                                            await processing_msg.edit(content="✅ 文字起こしと議事録化は完了しましたが、\n❌ Google Docsへの保存に失敗しました。")
                                else:
                                    await processing_msg.edit(content="✅ 文字起こしは完了しましたが、\n❌ 議事録化に失敗しました。")
                                
                                # 文字起こし成功後、ローカルの音声ファイルを削除
                                try:
                                    if os.path.exists(local_path):
                                        os.remove(local_path)
                                        print(f"ローカル音声ファイルを削除しました: {local_path}")
                                except Exception as e:
                                    print(f"ローカル音声ファイルの削除中にエラーが発生しました: {e}")
                            else:
                                await processing_msg.edit(content="❌ 文字起こしに失敗しました。")
                                
                                # 文字起こし失敗後もローカルの音声ファイルを削除
                                try:
                                    if os.path.exists(local_path):
                                        os.remove(local_path)
                                        print(f"ローカル音声ファイルを削除しました: {local_path}")
                                except Exception as e:
                                    print(f"ローカル音声ファイルの削除中にエラーが発生しました: {e}")
                        except Exception as e:
                            print(f"文字起こし処理中にエラーが発生しました: {e}")
                            await processing_msg.edit(content=f"❌ 文字起こし処理中にエラーが発生しました: {str(e)}")
                            
                            # 例外発生時もローカルの音声ファイルを削除
                            try:
                                if os.path.exists(local_path):
                                    os.remove(local_path)
                                    print(f"ローカル音声ファイルを削除しました: {local_path}")
                            except Exception as del_err:
                                print(f"ローカル音声ファイルの削除中にエラーが発生しました: {del_err}")
                    except Exception as e:
                        print(f"音声ファイルのエクスポート中にエラーが発生しました: {e}")
            except Exception as e:
                print(f"一時ファイル処理中にエラーが発生しました: {e}")
            finally:
                # 一時ファイルを削除（エラー処理追加）
                try:
                    for temp_file in temp_files:
                        try:
                            if os.path.exists(temp_file):
                                os.remove(temp_file)
                        except Exception as e:
                            print(f"一時ファイル削除中にエラーが発生しました: {temp_file} - {e}")
                    
                    # 一時ディレクトリを削除
                    if os.path.exists(temp_dir_path):
                        try:
                            os.rmdir(temp_dir_path)
                        except Exception as e:
                            print(f"一時ディレクトリ削除中にエラーが発生しました: {temp_dir_path} - {e}")
                except Exception as e:
                    print(f"一時ファイルのクリーンアップ中にエラーが発生しました: {e}")

def setup(bot):
    bot.add_cog(RecordingCog(bot))