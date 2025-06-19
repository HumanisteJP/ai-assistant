# Yata-Agent (日本語版)

Yata-Agentは、Discordのボイスチャンネルでの会話を録音し、文字起こしを行い、議事録をGoogleドキュメントに保存するDiscordボットです。

このプロジェクトは、オリジナルのYata_legacyを、モダンでスケーラブル、かつテスト可能なアーキテクチャでリファクタリングしたものです。

## アーキテクチャ

このアプリケーションは、関心の分離と保守性を確保するため、クリーンなレイヤードアーキテクチャに従っています。

- **Cogs (インターフェース層)**: Discordのコマンドとユーザーインタラクションを処理します。
- **Services (ビジネスロジック層)**: アプリケーションの中核となるロジックを実装します。
- **Data (データアクセス層)**: データベース（SQLite）によるデータの永続化を管理します。

アプリケーション全体で依存性注入（DI）が使用されており、軽量な`container`によって管理されています。これにより、コンポーネントを疎結合に保ち、テストを容易にします。

## 主な機能

- **/record_start**: ユーザーがいるボイスチャンネルで録音を開始します。
- **/record_stop**: 録音を停止し、音声を処理して、議事録をGoogleドキュメントにアップロードします。
- **/setup**: Google DriveのフォルダIDなど、サーバー固有の設定を行います。
- **/google_auth**: DMを介してGoogleアカウントの認証プロセスを開始します。

## セットアップとインストール

### 1. 前提条件

- Python 3.11以降
- `uv`（環境管理に推奨）

### 2. リポジトリをクローンする

```bash
git clone <repository_url>
cd yata-agent
```

### 3. 仮想環境の作成

仮想環境の使用を強く推奨します。

```bash
uv venv
source .venv/bin/activate  # Windowsの場合は `.venv\Scripts\activate` を使用
```

### 4. 依存関係のインストール

`uv`を使用して、必要なPythonパッケージをインストールします。

```bash
uv pip sync pyproject.toml
```

### 5. `.env` ファイルの作成

このアプリケーションは、APIキーと設定のためにいくつかの環境変数を必要とします。`yata-agent`ディレクトリに、サンプルファイルをコピーして`.env`という名前のファイルを作成します。

```bash
cp .env.example .env
```

次に、`.env`ファイルを開き、以下の変数に値を設定してください。

- `DISCORD_TOKEN`: あなたのDiscordボットのトークン。
- `OPENAI_API_KEY`: 文字起こし（Whisper）用のOpenAI APIキー。
- `CLIENT_SECRETS_JSON`: Google Cloud Consoleから取得した`client_secrets.json`の内容を、1行の文字列として貼り付けます。
- `REDIRECT_URI`: Google Cloudプロジェクトで設定したOAuth 2.0のリダイレクトURI（例: `http://localhost:8000/oauth2callback`）。
- `DB_PATH`: SQLiteデータベースファイルのパス（例: `yata_agent.db`）。

### 6. ボットの実行

セットアップが完了したら、ボットを実行できます。

```bash
python src/main.py
```

ボットと、OAuthコールバック用のFastAPIサーバーが同時に起動します。

## テストの実行

テストスイートを実行するには、`pytest`を使用します。

```bash
pytest
``` 