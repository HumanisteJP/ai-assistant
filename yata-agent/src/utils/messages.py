from __future__ import annotations

"""Centralised bilingual (JA/EN) message catalog."""

from typing import Final, Mapping

_MESSAGES: Final[Mapping[str, tuple[str, str]]] = {
    "guild_only": (
        "このコマンドはサーバー内でのみ実行できます。",
        "This command can only be used inside a server (guild).",
    ),
    "need_setup": (
        "❌ まず `/setup` を実行してサーバー設定を登録してください。",
        "❌ Please run `/setup` first to configure this server.",
    ),
    "need_auth": (
        "❌ `/google_auth` を実行して Google アカウントと連携してください。",
        "❌ Run `/google_auth` to connect your Google account.",
    ),
    "ready": (
        "✅ すべての準備が整っています！ `/record_start` で録音を開始できます。",
        "✅ All set! You can start recording with `/record_start`.",
    ),
    "auth_url_sent": (
        "✅ 認証用のURLをダイレクトメッセージに送信しました。DMを確認してください。",
        "✅ Sent the authentication URL to you via Direct Message. Please check your DMs.",
    ),
    "record_start": (
        "✅ 録音を開始しました。/record_stop で停止します。",
        "✅ Recording started. Use /record_stop to stop.",
    ),
    "record_already": (
        "⚠️ すでに録音中です。/record_stop で停止してください。",
        "⚠️ Recording is already in progress. Please stop it with /record_stop.",
    ),
    "voice_join_first": (
        "❌ 先にボイスチャンネルへ参加してください。",
        "❌ Please join a voice channel first.",
    ),
    "record_stop_no_record": (
        "❌ 現在録音は行われていません。",
        "❌ Recording is not currently running.",
    ),
    "record_stop_done": (
        "⏹️ 録音を停止しました。録音データを処理します…",
        "⏹️ Recording stopped. Processing the audio…",
    ),
}


def msg(key: str) -> str:
    """Return combined JA + EN message for *key*."""
    ja, en = _MESSAGES[key]
    return f"{ja}\n{en}"

__all__ = ["msg"] 