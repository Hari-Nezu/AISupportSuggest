"""LLM バックエンド統合（Anthropic API / Ollama）。"""
from __future__ import annotations

import base64
import json as _json

import requests

from src.config import (
    ANTHROPIC_API_KEY,
    OLLAMA_BASE_URL,
    OLLAMA_MODEL,
    OLLAMA_TIMEOUT,
    OLLAMA_VISION_MODEL,
    USE_ANTHROPIC,
)


# ── Ollama ────────────────────────────────────────────────────────────────────

def query_ollama(prompt: str, model: str | None = None) -> str:
    """ストリーミングで Ollama にリクエストし、全チャンクを結合して返す。
    OLLAMA_TIMEOUT はチャンク間の read タイムアウトであり、
    モデルの応答速度に依存しないため事実上タイムアウトしない。
    """
    model = model or OLLAMA_MODEL
    try:
        response = requests.post(
            f"{OLLAMA_BASE_URL}/api/generate",
            json={"model": model, "prompt": prompt, "stream": True},
            stream=True,
            timeout=(10, OLLAMA_TIMEOUT),  # (connect_timeout, read_timeout)
        )
        response.raise_for_status()
        parts: list[str] = []
        for raw_line in response.iter_lines():
            if not raw_line:
                continue
            chunk = _json.loads(raw_line)
            parts.append(chunk.get("response", ""))
            if chunk.get("done"):
                break
        return "".join(parts)
    except requests.exceptions.ConnectionError:
        raise RuntimeError(
            "Ollama に接続できません。\n`ollama serve` を実行してから再試行してください。"
        )
    except requests.exceptions.Timeout:
        raise RuntimeError(
            f"Ollama がタイムアウトしました（チャンク間 {OLLAMA_TIMEOUT} 秒）。\n"
            "config.py の OLLAMA_TIMEOUT を大きくするか、より小さいモデルを使用してください。"
        )
    except Exception as e:
        raise RuntimeError(f"Ollama エラー: {e}")


# ── Anthropic ─────────────────────────────────────────────────────────────────

def query_anthropic(prompt: str) -> str:
    try:
        import anthropic
    except ImportError:
        raise RuntimeError("anthropic パッケージが未インストールです。`pip install anthropic`")

    if not ANTHROPIC_API_KEY:
        raise RuntimeError("ANTHROPIC_API_KEY が設定されていません。")

    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    message = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=2048,
        messages=[{"role": "user", "content": prompt}],
    )
    return message.content[0].text


# ── 統合エントリ ──────────────────────────────────────────────────────────────

def query_llm(prompt: str) -> str:
    if USE_ANTHROPIC and ANTHROPIC_API_KEY:
        return query_anthropic(prompt)
    return query_ollama(prompt)
