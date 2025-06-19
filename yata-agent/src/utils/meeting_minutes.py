"""Generate structured meeting minutes from raw transcript text using OpenAI Chat Completion API.

This utility is intentionally *stateless* so that it can be imported from
anywhere (Service 層推奨) without introducing additional dependencies.
"""
from __future__ import annotations

import os
from typing import Optional

import openai

_OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")

_TEMPLATE = (
    "1.目的\n"
    "2.前提\n"
    "3.アジェンダ\n"
    "4.記録\n"
    "5.todo\n\n"
    "# 目的\n1. 話し合いの目的を書いてください\n\n"
    "# 前提\n1. 話し合う上で前提となる情報を共有してください\n\n"
    "# アジェンダ\n1. 話し合いの全体の流れや内容をまとめたもの\n\n"
    "# 記録\n1. 話し合いの結果決定したことを記録してください。できるだけ詳細に会議で話し合ったことを書くこと。\n\n"
    "# ToDo\n1. 各メンバーに対して話し合いの結果決定したToDoを整理しましょう\n"
)

_SYSTEM_PROMPT = (
    "あなたは会議の議事録を整理する専門家です。与えられた書き起こしから、"
    "重要な情報を抽出しテンプレートに沿って整理してください。当てはまらないセクションは空欄で構いません。"
)

_MODEL = "gpt-4o-mini"  # 2025-06 時点の lightweight GPT-4o family


def format_meeting_minutes(transcript: str) -> Optional[str]:
    """Return formatted meeting minutes text or *None* on error."""
    import logging
    logger = logging.getLogger(__name__)
    
    logger.info(f"format_meeting_minutes called with transcript length: {len(transcript)}")
    logger.info(f"Transcript sample: {transcript[:100]}...")
    
    if not _OPENAI_API_KEY:
        logger.warning("OPENAI_API_KEY not found, returning None")
        # 上位で別の手段にフォールバックできるよう None を返す
        return None

    try:
        client = openai.OpenAI(api_key=_OPENAI_API_KEY)
        prompt = (
            "以下の会議の書き起こしを、以下のテンプレートに沿って整理してください。\n\n"
            f"テンプレート:\n{_TEMPLATE}\n\n"
            f"会議の書き起こし:\n{transcript}"
        )
        logger.info("Sending request to OpenAI chat completions API...")
        response = client.chat.completions.create(
            model=_MODEL,
            messages=[
                {"role": "system", "content": _SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ],
            temperature=0.7,
            max_tokens=2048,
        )
        result = response.choices[0].message.content
        logger.info(f"OpenAI response received, length: {len(result) if result else 0}")
        logger.info(f"Response sample: {result[:100] if result else 'None'}...")
        return result
    except Exception as e:
        logger.error(f"Error in format_meeting_minutes: {e}")
        return None 