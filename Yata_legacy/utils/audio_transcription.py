import os
from dotenv import load_dotenv
import openai
import subprocess
import tempfile
from pydub import AudioSegment

# .envファイルから環境変数をロード
load_dotenv()

# 環境変数からAPIキーを取得
api_key = os.getenv("OPENAI_API_KEY")

# Whisper APIのファイルサイズ上限（25MB）
MAX_FILE_SIZE_MB = 25
MAX_FILE_SIZE_BYTES = MAX_FILE_SIZE_MB * 1024 * 1024

def compress_audio(input_file_path):
    """
    pydubを使用して音声ファイルを圧縮する関数
    
    引数:
        input_file_path (str): 圧縮する音声ファイルのパス
    
    戻り値:
        str: 圧縮された音声ファイルのパス
    """
    # 一時ファイルを作成
    with tempfile.NamedTemporaryFile(suffix='.ogg', delete=False) as temp_file:
        output_file_path = temp_file.name
    
    try:
        # 元のサイズを記録
        original_size = os.path.getsize(input_file_path) / (1024 * 1024)
        
        # 音声ファイルを読み込む
        audio = AudioSegment.from_file(input_file_path)
        
        # モノラルに変換（ステレオの場合）
        if audio.channels > 1:
            audio = audio.set_channels(1)
        
        # サンプルレートを下げる（オプション）
        audio = audio.set_frame_rate(16000)  # 16kHzは音声認識に十分
        
        # 音質設定を指定してエクスポート
        # pydubでは直接ビットレートを指定できないので、quality設定で代用
        export_params = {
            "format": "ogg",
            "codec": "libopus",
            "parameters": ["-application", "voip", "-b:a", "12k"]
        }
        
        # 圧縮してエクスポート
        audio.export(output_file_path, **export_params)
        
        # 圧縮後のサイズを計算
        compressed_size = os.path.getsize(output_file_path) / (1024 * 1024)
        
        print(f"音声ファイルを圧縮しました: {input_file_path} -> {output_file_path}")
        print(f"元のサイズ: {original_size:.2f}MB")
        print(f"圧縮後のサイズ: {compressed_size:.2f}MB")
        
        return output_file_path
    
    except Exception as e:
        print(f"音声ファイル圧縮中にエラーが発生しました: {str(e)}")
        # エラーが発生した場合は一時ファイルを削除
        if os.path.exists(output_file_path):
            os.remove(output_file_path)
        return None

def transcribe_audio(audio_file_path, language="ja"):
    """
    音声ファイルをOpenAIのWhisperモデルを使用して文字起こしする関数
    
    引数:
        audio_file_path (str): 文字起こしする音声ファイルのパス
        language (str): 音声の言語（デフォルト: 日本語）
    
    戻り値:
        str: 文字起こしされたテキスト
    """
    try:
        # APIキーが設定されているか確認
        if not api_key:
            raise ValueError("OPENAI_API_KEYが設定されていません。.envファイルを確認してください。")
        
        compressed_file_path = None
        
        compressed_file_path = compress_audio(audio_file_path)

        if not compressed_file_path:
            raise ValueError("音声ファイルの圧縮に失敗しました。")
        audio_file_path = compressed_file_path

        # OpenAIクライアントを初期化
        client = openai.OpenAI(api_key=api_key)
        
        # 音声ファイルを開く
        with open(audio_file_path, "rb") as audio_file:
            # Whisper APIを使用して文字起こし
            transcript = client.audio.transcriptions.create(
                model="whisper-1",
                file=audio_file,
                language=language
            )
        
        # 圧縮した一時ファイルを削除
        if compressed_file_path and os.path.exists(compressed_file_path):
            os.remove(compressed_file_path)
            print(f"一時ファイルを削除しました: {compressed_file_path}")
        
        # 文字起こし結果を返す
        return transcript.text
    
    except Exception as e:
        # 圧縮した一時ファイルを削除（エラー発生時）
        if compressed_file_path and os.path.exists(compressed_file_path):
            os.remove(compressed_file_path)
            print(f"一時ファイルを削除しました: {compressed_file_path}")
        
        print(f"文字起こし中にエラーが発生しました: {str(e)}")
        return None

# 使用例:
# テキスト = transcribe_audio("path/to/audio/file.mp3") 