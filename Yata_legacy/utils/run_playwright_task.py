import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
import json
from typing import Optional
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError
import base64

def get_page_html(url: str):
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch()
            page = browser.new_page()
            page.goto(url)
            page.wait_for_load_state('networkidle')
            try:
                page.wait_for_selector('article', timeout=10000)
            except PlaywrightTimeoutError:
                pass  # 記事がなければ無視
            html = page.content()
            browser.close()
        return {"status": "success", "html": html}
    except Exception as e:
        return {"status": "error", "error_message": str(e)}

def extract_text_by_selector(url: str, selector: str):
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch()
            page = browser.new_page()
            page.goto(url)
            page.wait_for_load_state('networkidle')
            try:
                page.wait_for_selector(selector, timeout=10000)
            except PlaywrightTimeoutError:
                pass
            elements = page.query_selector_all(selector)
            texts = [el.inner_text() for el in elements]
            browser.close()
        return {"status": "success", "texts": texts}
    except Exception as e:
        return {"status": "error", "error_message": str(e)}

def take_screenshot(url: str, selector: Optional[str], path: str):
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch()
            page = browser.new_page()
            page.goto(url)
            if selector:
                element = page.query_selector(selector)
                if element:
                    element.screenshot(path=path)
                else:
                    browser.close()
                    return {"status": "error", "error_message": f"Selector '{selector}' not found."}
            else:
                page.screenshot(path=path, full_page=True)
            browser.close()
        # 画像バイナリをbase64で返す
        with open(path, "rb") as f:
            image_base64 = base64.b64encode(f.read()).decode("utf-8")
        return {"status": "success", "path": path, "image_base64": image_base64}
    except Exception as e:
        return {"status": "error", "error_message": str(e)}

def main():
    if len(sys.argv) < 3:
        print(json.dumps({"status": "error", "error_message": "Insufficient arguments."}))
        sys.exit(1)
    task = sys.argv[1]
    if task == "get_page_html":
        url = sys.argv[2]
        result = get_page_html(url)
    elif task == "extract_text_by_selector":
        if len(sys.argv) < 4:
            print(json.dumps({"status": "error", "error_message": "Insufficient arguments for extract_text_by_selector."}))
            sys.exit(1)
        url = sys.argv[2]
        selector = sys.argv[3]
        result = extract_text_by_selector(url, selector)
    elif task == "take_screenshot":
        if len(sys.argv) < 4:
            print(json.dumps({"status": "error", "error_message": "Insufficient arguments for take_screenshot."}))
            sys.exit(1)
        url = sys.argv[2]
        path = sys.argv[3]
        selector = sys.argv[4] if len(sys.argv) > 4 else None
        result = take_screenshot(url, selector, path)
    else:
        result = {"status": "error", "error_message": f"Unknown task: {task}"}
    print(json.dumps(result, ensure_ascii=False))

if __name__ == "__main__":
    main() 