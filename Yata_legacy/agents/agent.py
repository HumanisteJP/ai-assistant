from google.adk.agents.llm_agent import LlmAgent
import os
import sys
from dotenv import load_dotenv
from pathlib import Path

# 親ディレクトリをパスに追加
sys.path.append(str(Path(__file__).parent))
from utils.oauth_server import get_auth_url
from utils.web import get_page_html, extract_text_by_selector

# .envファイルから環境変数をロード
load_dotenv()

root_agent = LlmAgent(
        name="yata_team_coordinator",
        model="gemini-2.0-flash-lite",
        description="Yataプロジェクトの複数のエージェントを統合したチームコーディネーター",
        instruction="""
        あなたはYata。ユーザーを助けるエージェントです。親切で丁寧に回答してください。

        **利用可能なツール:**
        - get_page_html: 指定URLのHTML全体を取得

        **対応方針:**
        1. ユーザーの意図を正確に把握し、最適なツールを選択する
        2. 取得した情報は分かりやすく整理して提示する
        3. 必要に応じて追加の抽出や再試行を提案する
        4. エラーが発生した場合は原因を説明し、代替案を示す

        **例:**
        - 「このURLのページを見せて」→ get_page_html
        """,
        tools=[get_page_html],
)
    
