import subprocess
import sys
import json
import os
from typing import Dict, Any, Optional

RUNNER = os.path.join(os.path.dirname(__file__), "run_playwright_task.py")

# 1. ページのHTML取得
def get_page_html(url: str) -> Dict[str, Any]:
    """
    指定したURLのページHTMLを取得します。

    Args:
        url: 取得対象のWebページURL。
    Returns:
        dict: {"status": "success", "html": <HTML文字列>} または {"status": "error", "error_message": <説明>}
    """
    try:
        result = subprocess.run(
            [sys.executable, RUNNER, "get_page_html", url],
            capture_output=True, text=True, check=True, encoding="utf-8"
        )
        return json.loads(result.stdout)
    except subprocess.CalledProcessError as e:
        print("[subprocess stderr]", e.stderr)
        return {"status": "error", "error_message": str(e)}
    except Exception as e:
        return {"status": "error", "error_message": str(e)}

# 2. 要素のテキスト抽出
def extract_text_by_selector(url: str, selector: str) -> Dict[str, Any]:
    """
    指定URLの指定セレクタのテキストを抽出します。

    Args:
        url: 対象WebページのURL。
        selector: CSSセレクタ。
    Returns:
        dict: {"status": "success", "texts": [テキストリスト]} または {"status": "error", "error_message": <説明>}
    """
    try:
        result = subprocess.run(
            [sys.executable, RUNNER, "extract_text_by_selector", url, selector],
            capture_output=True, text=True, check=True, encoding="utf-8"
        )
        return json.loads(result.stdout)
    except subprocess.CalledProcessError as e:
        print("[subprocess stderr]", e.stderr)
        return {"status": "error", "error_message": str(e)}
    except Exception as e:
        return {"status": "error", "error_message": str(e)}

# 3. スクリーンショット取得
def take_screenshot(url: str, selector: Optional[str] = None, path: str = "screenshot.png") -> Dict[str, Any]:
    """
    指定URLのページ全体または特定要素のスクリーンショットを取得します。

    Args:
        url: 対象WebページのURL。
        selector: スクリーンショットを撮る要素のCSSセレクタ（省略時はページ全体）。
        path: 保存先ファイルパス。
    Returns:
        dict: {"status": "success", "path": <保存先パス>, "image_base64": <image_base64>} または {"status": "error", "error_message": <説明>}
    """
    try:
        args = [sys.executable, RUNNER, "take_screenshot", url, path]
        if selector:
            args.append(selector)
        result = subprocess.run(
            args,
            capture_output=True, text=True, check=True, encoding="utf-8"
        )
        return json.loads(result.stdout)
    except subprocess.CalledProcessError as e:
        print("[subprocess stderr]", e.stderr)
        return {"status": "error", "error_message": str(e)}
    except Exception as e:
        return {"status": "error", "error_message": str(e)}
