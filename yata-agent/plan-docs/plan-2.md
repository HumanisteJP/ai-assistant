# EC2 / VPS Deployment – OAuth Callback Plan

## 方針
Discord Bot (py-cord) と Google OAuth 2.0 のコールバック HTTP サーバー (FastAPI + uvicorn) を **同一 Python プロセス & 同一イベントループ** に同居させる。

## 採用理由
1. **DI が容易**  
   Bot と FastAPI が同じメモリ空間にあるため、`google_service` などのインスタンスを簡単に共有できる。
2. **運用コスト最小**  
   systemd / Supervisor / Docker で 1 サービス(コンテナ)管理。ログも１系統。
3. **リソース効率**  
   VPS はメモリが限られがち。同一プロセスなら最小フットプリント。
4. **スケール要件が軽い**  
   OAuth コールバックは低トラフィック。uvicorn 1 worker で十分。

## 実装概要
1. **FastAPI ルート**  
   `@app.get("/oauth2callback")` で `code` & `state` を受信し、
   `await google_service.exchange_code_for_credentials(guild_id, code)` を実行。
2. **main.py** での起動順序
   ```python
   app = FastAPI()
   bot = commands.Bot(...)
   
   # FastAPI サーバーをバックグラウンドで起動
   server = uvicorn.Server(uvicorn.Config(app, host="0.0.0.0", port=8000))
   asyncio.create_task(server.serve())
   
   # Discord Bot 起動
   await bot.start(DISCORD_TOKEN)
   ```
3. **TLS 終端**  
   VPS の 443/80 は Nginx/Caddy で受け、`proxy_pass http://127.0.0.1:8000;` で転送。
4. **Graceful Shutdown**  
   Bot 側の `on_shutdown` で `server.should_exit = True` をセット。
5. **将来拡張**  
   高可用性が必要なら FastAPI 部分だけ別プロセス化 / LB 配下へ移行可。

---
この方針を基に `src/main.py` に統合エントリポイントを実装する。
