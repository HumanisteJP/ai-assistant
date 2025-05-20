from google.adk.agents.llm_agent import LlmAgent
import os
import sys
from dotenv import load_dotenv
from pathlib import Path

# 親ディレクトリをパスに追加
sys.path.append(str(Path(__file__).parent))

# 各エージェントのインポート
from .google_docs_agent import google_docs_agent
from .google_drive_search_agent import google_drive_search_agent
# .envファイルから環境変数をロード
load_dotenv()

root_agent = LlmAgent(
        name="yata_team_coordinator",
        model="gemini-2.0-flash-lite",
        description="Yataプロジェクトの複数のエージェントを統合したチームコーディネーター",
        instruction="""
        あなたはYata。ユーザーを助けるエージェントです。親切で丁寧に回答してください。
        """,
)
    
