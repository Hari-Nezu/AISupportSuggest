"""
提案表示ウィンドウ（単独プロセスとして起動される）。
引数にテキストファイルのパスを受け取り、内容を表示する。
"""
import html
import sys
import tempfile
import webbrowser
from pathlib import Path


def show(text: str):
    escaped = html.escape(text)
    html_content = f"""<!DOCTYPE html>
<html lang="ja">
<head>
<meta charset="UTF-8">
<title>AI省力化提案</title>
<style>
  body {{
    background: #1e1e2e;
    color: #cdd6f4;
    font-family: "Helvetica Neue", Helvetica, sans-serif;
    font-size: 14px;
    margin: 0;
    padding: 20px 24px 24px;
  }}
  h1 {{
    font-size: 18px;
    font-weight: bold;
    margin: 0 0 16px;
    padding-bottom: 10px;
    border-bottom: 1px solid #45475a;
  }}
  pre {{
    background: #313244;
    border-radius: 8px;
    padding: 16px;
    white-space: pre-wrap;
    word-break: break-word;
    line-height: 1.6;
    font-family: inherit;
    font-size: 13px;
  }}
</style>
</head>
<body>
<h1>AI省力化提案</h1>
<pre>{escaped}</pre>
</body>
</html>"""

    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".html", encoding="utf-8", delete=False
    ) as f:
        f.write(html_content)
        tmp_path = f.name

    webbrowser.open(f"file://{tmp_path}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python -m src.ui.suggestion_viewer <text_file_path>")
        sys.exit(1)

    file_path = sys.argv[1]
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()
    except Exception as e:
        content = f"ファイルの読み込みに失敗しました: {e}"

    show(content)
