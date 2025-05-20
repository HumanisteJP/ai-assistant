import os
import pickle
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from google_auth_oauthlib.flow import Flow
from dotenv import load_dotenv
import uvicorn
import threading
import time
from typing import Dict, Optional

# .envファイルから環境変数をロード
load_dotenv()

# Google Docs APIのスコープ
SCOPES = ['https://www.googleapis.com/auth/documents', 'https://www.googleapis.com/auth/drive']

# サーバーの設定
HOST = "localhost"
PORT = 8000
# 外部からアクセス可能なベースURL（ngrok等を使用する場合に設定）
REDIRECT_BASE_URL = os.getenv("REDIRECT_BASE_URL", f"http://{HOST}:{PORT}")

# 認証コールバックパス - GCP側での設定を統一するために固定パスを使用
CALLBACK_PATH = "/oauth2callback"

# Discord サーバーごとの認証状態を保存
auth_state: Dict[str, Dict] = {}

app = FastAPI()

@app.get("/")
async def root():
    return {"message": "OAuth認証サーバーが稼働中です"}

@app.get("/authorize/{guild_id}")
async def authorize(guild_id: str):
    """
    認証URLを生成する
    """
    # デバッグ情報を追加
    redirect_uri = f"{REDIRECT_BASE_URL}{CALLBACK_PATH}"
    print(f"[DEBUG] REDIRECT_BASE_URL: {REDIRECT_BASE_URL}")
    print(f"[DEBUG] 使用するリダイレクトURI: {redirect_uri}")
    
    # credentials.jsonからフローを作成
    flow = Flow.from_client_secrets_file(
        'credentials.json',
        scopes=SCOPES,
        redirect_uri=redirect_uri
    )
    
    # 認証URLを生成
    auth_url, state = flow.authorization_url(
        access_type='offline',
        include_granted_scopes='true',
        prompt='consent',  # 常に同意画面を表示して、refresh_tokenを確実に取得
        state=guild_id  # state パラメータにサーバーIDを含める
    )
    
    # デバッグ情報を追加
    print(f"[DEBUG] 生成された認証URL: {auth_url}")
    print(f"[DEBUG] StateパラメータにサーバーID({guild_id})を含めました")
    
    # フローを一時的に保存
    auth_state[state] = {"flow": flow, "guild_id": guild_id}
    
    return {"auth_url": auth_url}

@app.get(CALLBACK_PATH, response_class=HTMLResponse)
async def callback(request: Request):
    """
    OAuthコールバックを処理する
    """
    # URLからコードとステートを取得
    code = request.query_params.get("code")
    state = request.query_params.get("state")
    
    print(f"[DEBUG] コールバック受信: state={state}")
    
    if not code or not state or state not in auth_state:
        return "<html><body><h1>認証に失敗しました</h1><p>DiscordボットでOAuth認証を再実行してください</p></body></html>"
    
    # 保存したフローとguild_idを取得
    flow = auth_state[state]["flow"]
    guild_id = auth_state[state]["guild_id"]
    
    # コードを使ってトークンを取得
    flow.fetch_token(code=code)
    
    # 認証情報を取得
    credentials = flow.credentials
    
    # サーバーIDごとにトークンを保存
    token_path = f'token_{guild_id}.pickle'
    with open(token_path, 'wb') as token:
        pickle.dump(credentials, token)
    
    print(f"[DEBUG] サーバーID {guild_id} の認証トークンを保存しました")
    
    # 認証状態をクリア
    auth_state.pop(state, None)
    
    return """
    <html>
        <body>
            <h1>認証が完了しました</h1>
            <p>このウィンドウを閉じて、Discordボットに戻ってください。</p>
        </body>
    </html>
    """

# サーバーを起動する関数
def start_server():
    uvicorn.run(app, host=HOST, port=PORT)

# サーバーをバックグラウンドで起動する
def run_oauth_server():
    server_thread = threading.Thread(target=start_server)
    server_thread.daemon = True  # メインプログラムが終了したら一緒に終了するように
    server_thread.start()
    return server_thread

def get_auth_url(guild_id: str) -> str:
    """
    Discordボット用に認証URLを取得する関数
    """
    import requests
    try:
        response = requests.get(f"http://{HOST}:{PORT}/authorize/{guild_id}")
        data = response.json()
        return data.get("auth_url", "")
    except Exception as e:
        print(f"[ERROR] 認証URL取得中にエラー発生: {e}")
        return ""

if __name__ == "__main__":
    # 単体テスト用：サーバーを直接起動
    uvicorn.run(app, host=HOST, port=PORT)