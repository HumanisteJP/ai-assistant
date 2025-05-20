# Discord録音Bot

Discordボイスチャットの会話を録音し、MP3ファイルとして保存するBotです。Discord.pyの拡張機能であるCogsを使用して機能ごとにコードを分割し、保守性の高い構造になっています。

## 主な機能

- ボイスチャットの会話を録音
- 複数サーバーでの同時利用（各サーバーで1つのボイスチャンネルに接続可能）
- 録音データをMP3形式で保存
- スラッシュコマンド対応

## セットアップ

### 必要条件

- Python 3.8以上
- 必要なパッケージ: discord.py, pydub, python-dotenv

### インストール

1. リポジトリをクローンまたはダウンロード
2. 必要なパッケージをインストール

```bash
pip install -r requirements.txt
```

3. `.env`ファイルを作成し、Botのトークンを設定

```
DISCORD_TOKEN=あなたのBotトークン
RECORDINGS_DIR=./recordings  # 録音の保存先（オプション）
```

### 実行方法

```bash
python main.py
```

## コマンド一覧

### スラッシュコマンド

- `/record_start` - ボイスチャンネルでの録音を開始
- `/record_stop` - 録音を停止してファイルを保存

### 通常コマンド（プレフィックス: `!`）

- `!record_start` - ボイスチャンネルでの録音を開始
- `!record_stop` - 録音を停止してファイルを保存

### 管理者用コマンド

- `!cog list` - 利用可能なCogの一覧を表示
- `!cog load <name>` - Cogをロード
- `!cog unload <name>` - Cogをアンロード
- `!cog reload <name>` - Cogをリロード
- `!shutdown` - Botをシャットダウン（管理者のみ）

## Cog機能の解説

このBotは`discord.py`の`Cog`システムを使って機能ごとにコードを分割しています。

### Cogとは

Cogは関連する機能をグループ化する方法で、クラスベースでコマンドと機能を整理できます。これにより:

- コードの整理: 関連するコマンドを一つのクラスにまとめる
- 機能の動的ロード: Botを再起動せずに機能を追加・削除・更新できる
- イベントハンドリング: Cogごとに独自のイベントハンドラを設定

### 主なCog

- `recording.py` - 録音機能のすべてのコマンドとロジック
- `example.py` - Cogの様々な機能を示すサンプル（スラッシュコマンド、通常コマンド、イベントリスナーなど）
- `advanced_example.py` - Cogの管理機能を含む高度な例（ロード、アンロード、リロード）

### Cogの作成方法

新しいCogを作成するには:

1. `cogs`フォルダ内に新しいPythonファイルを作成
2. `commands.Cog`を継承したクラスを定義
3. `setup`関数でBotにCogを登録

```python
from discord.ext import commands

class MyCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        
    @commands.command()
    async def mycommand(self, ctx):
        await ctx.send("Hello!")

def setup(bot):
    bot.add_cog(MyCog(bot))
```

## 参考リンク

- [Discord.py ドキュメント](https://discordpy.readthedocs.io/)
- [Discord Developer Portal](https://discord.com/developers/applications) 