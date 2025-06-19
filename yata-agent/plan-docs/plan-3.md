```bash
pytest -q
```

Ran tool

Read file: yata-agent/tests/test_services/test_google_service.py

Read file: yata-agent/tests/test_services/test_processing_service.py

Read file: yata-agent/src/cogs/setup_cog.py

Read file: yata-agent/src/cogs/recording_cog.py

Read file: yata-agent/src/services/google_service.py

Read file: yata-agent/src/services/transcription_service.py

Read file: yata-agent/src/services/database_service.py

Read file: yata-agent/src/data/database.py

Read file: yata-agent/tests/test_cogs/test_recording_cog.py

Read file: yata-agent/pyproject.toml

🔥 これまでの実装（tests 26 本すべて PASSED）で
• Data / Service / Cog 層の基本機能  
• DB スキーマ & DI の土台  
• Google / Whisper / Processing の主要ロジック  
までは完了しています。  
残タスクは「本番運用に必要な“繋ぎ込み”と自動テストの拡充」が中心です。  
以下、優先度順のロードマップを提示します。  

────────────────────────────────────────
◆ 0. 現状の確認
────────────────────────────────────────
✓ tests すべて成功  
✓ DBService・GoogleService・ProcessingService 実装済  
✗ FastAPI + Discord Bot の統合エントリポイントが未実装  
✗ 依存注入を main に統一／Cog から仮実装排除  
✗ OAuth2 コールバックルート `/oauth2callback` 未実装  
✗ ユーザーが Google 認可 URL を取得するワークフロー未整備  
✗ CI／運用ドキュメント未整備

────────────────────────────────────────
◆ 1. エントリポイント統合（plan-2.md）
────────────────────────────────────────
1-1. `src/main.py` 追加  
    • FastAPI `app = FastAPI()`  
    • Discord `bot = commands.Bot(intents=intents)`  
    • `/oauth2callback` ルート実装  
      - query `code` と `state` から `guild_id` を抽出して  
        `await google_service.exchange_code_for_credentials(guild_id, code)`  
      - 成功時は任意の HTML/Discord へのリダイレクトを返却  
    • `uvicorn.Server` を `asyncio.create_task()` で起動  
    • `await bot.start(DISCORD_TOKEN)` で同一イベントループに載せる  
    • `python -m yata_agent` で実行出来る CLI エントリを `pyproject.toml [project.scripts]` に追加  

1-2. DI コンテナ（シンプル版）  
    • `src/container.py` で Service / Data 層を生成し singleton 保持  
    • Bot と FastAPI から同じインスタンスを import して再利用  

1-3. テスト  
    • `tests/test_main/test_oauth_callback.py`  
      - `AsyncClient(app)` で `/oauth2callback` hit  
      - GoogleService.exchange_code_for_credentials が await されるかを assert  
    • テスト用に Discord Bot は起動せず DI だけ差し替え(Dependency Override)  

────────────────────────────────────────
◆ 2. Cog の依存解決／仮コード排除
────────────────────────────────────────
2-1. `cogs.setup_cog.py` & `cogs.recording_cog.py`  
    • `async def setup(bot)` 内の **仮インスタンス生成** を削除  
    • 代わりに `bot.container` から service を取得して注入  
    • Bot 初期化時に `bot.container = container` をセット  

2-2. 新 Cog: `cogs/auth_cog.py`  
    • `/google_auth` コマンド  
       - `google_service.get_authentication_url(state=str(guild_id))`  
       - 生成 URL を DM か ephemral で返信  
    • テスト `tests/test_cogs/test_auth_cog.py`  
       - URL 生成呼び出し／followup.send を assert  

────────────────────────────────────────
◆ 3. GoogleService & Utility 拡充
────────────────────────────────────────
3-1. state のエンコード方式を統一  
    - 例: `state=f"gid:{guild_id}"` / callback 側で `split(":")[1]` で int 化  
    - テスト追加  

3-2. `GoogleService.get_authentication_url`  
    - 現在 `Flow.from_client_secrets_file(client_config=…)` は誤引数  
      → `Flow.from_client_config(self.client_config, scopes=…, redirect_uri=…)` に修正  
      (tests は patch していたため通っていた)  
    - 単体テスト修正  

────────────────────────────────────────
◆ 4. コンフィグ & デプロイ準備
────────────────────────────────────────
4-1. `.env.example` 生成  
    DISCORD_TOKEN, OPENAI_API_KEY, CLIENT_SECRETS_JSON, REDIRECT_URI, DB_PATH など  

4-2. `python-dotenv` で main 起動時に読み込み  
4-3. README 更新（EC2/VPS 手順、Nginx リバプロ例、systemd サービス例）  
4-4. Poetry/uv ロック更新 (`uv pip sync`)  

────────────────────────────────────────
◆ 5. CI / Lint / Format
────────────────────────────────────────
5-1. GitHub Actions  
    • `pytest` + `uv pip install -r pyproject.toml`  
    • `ruff` or `flake8` で lint  
5-2. pre-commit hooks に `pytest -q` & `ruff --fix`  

────────────────────────────────────────
◆ 6. 将来タスク（今回必須ではない）
────────────────────────────────────────
• Voice 録音実装を py-cord の `discord.FFmpegPCMAudio` ベースで実装  
• meeting_minutes アルゴリズムの品質向上（セクション自動抽出など）  
• マルチプロセス化（Bot と API を分離）／ヘルスチェックエンドポイント  
• Slash Command の国際化 (i18n)  

────────────────────────────────────────
◆ 実装順まとめ（Red-Green-Refactor を厳守）
────────────────────────────────────────
1. テスト追加（Fail → Red 状態）  
2. エントリポイント & DI 実装 → Green  
3. Cog 修正 → Green  
4. GoogleService 修正 → Green  
5. ドキュメント / CI → Refactor フェーズ仕上げ  

この順序で進めれば **常にテストが通る状態** を保ちながら plan-1 / plan-2 を完遂できます。