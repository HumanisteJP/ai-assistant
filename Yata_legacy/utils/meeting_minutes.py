import os
from dotenv import load_dotenv
import openai
from typing import Optional

# .envファイルから環境変数をロード
load_dotenv()

# 環境変数からAPIキーを取得
api_key = os.getenv("OPENAI_API_KEY")

def format_meeting_minutes(transcript: str) -> Optional[str]:
    """
    会議の書き起こしを議事録テンプレートに沿って整理する関数
    
    引数:
        transcript (str): 会議の書き起こしテキスト
    
    戻り値:
        str: 議事録テンプレートに沿って整理されたテキスト
    """
    try:
        # APIキーが設定されているか確認
        if not api_key:
            raise ValueError("OPENAI_API_KEYが設定されていません。.envファイルを確認してください。")
        
        # OpenAIクライアントを初期化
        client = openai.OpenAI(api_key=api_key)
        
        # プロンプトの作成
        prompt = f"""
以下の会議の書き起こしを、以下のテンプレートに沿って整理してください。
テンプレートの各セクションに適切な内容を記入し、不要な情報は省略してください。

テンプレート:
1.目的  
2.前提  
3.アジェンダ  
4.記録  
5.todo

# 目的
1. 話し合いの目的を書いてください

# 前提
1. 話し合う上で前提となる情報を共有してください

# アジェンダ
1. 話し合いの全体の流れや内容をまとめたもの

# 記録
1. 話し合いの結果決定したことを記録してください。できるだけ詳細に会議で話し合ったことを書くこと。

# ToDo
1. 各メンバーに対して話し合いの結果決定したToDoを整理しましょう

会議の書き起こし:
{transcript}
"""
        
        # GPT-4.1-nano-2025-04-14を使用して議事録を生成
        response = client.chat.completions.create(
            model="gpt-4.1-mini-2025-04-14",
            messages=[
                {"role": "system", "content": "あなたは会議の議事録を整理する専門家です。与えられた会議の書き起こしから、重要な情報を抽出し、テンプレートに沿って整理してください。ただし当てはまるものがない場合は空欄で構いません。"},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            max_tokens=2000
        )
        
        # 生成された議事録を返す
        return response.choices[0].message.content
    
    except Exception as e:
        print(f"議事録の生成中にエラーが発生しました: {str(e)}")
        return None

# 使用例:
# 議事録 = format_meeting_minutes("会議の書き起こしテキスト") 