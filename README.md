# 設計
記憶の永続化層はmem0を使用
ユーザーのメタ情報はmicroCMS上に保存

# インターフェース
Discordのボットとしての動作を予定
GoogleWorkspace連携も予定
GitHubのリポジトリ連携も予定

# AIモデル
OpenAIのGPT-4miniまたはgeminiを使用
予算が立てば他のモデル ClaudeやGPT-4oも使用

# ツール
ScrapyによるWebスクレイピング
金があればFireCrawlを使用
PlaywrightMCPを使う方が賢いか？→browser-useを使うのがよさそう　https://zenn.dev/gunjo/articles/2f6898b846d371
コンピュータユースによる計算やファイル処理も行いたいが技術的難度が高い

# 永続化層
## 開発段階
mem0のプラットフォームを利用

## 運用段階
Qdrant無料枠によるベクトルデータベースを利用
Neo4jは上手く設定で切れば利用

# Docker
Dockerを使用して再現性のある実行環境を構築



