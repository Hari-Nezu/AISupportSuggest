"""LLM バックエンド統合（Anthropic API / Ollama）。"""
from __future__ import annotations

import base64
from pathlib import Path

import requests

from src.config import (
    ANTHROPIC_API_KEY,
    OLLAMA_BASE_URL,
    OLLAMA_MODEL,
    OLLAMA_VISION_MODEL,
    USE_ANTHROPIC,
)


# ── Ollama ────────────────────────────────────────────────────────────────────

def query_ollama(prompt: str, model: str | None = None) -> str:
    model = model or OLLAMA_MODEL
    try:
        response = requests.post(
            f"{OLLAMA_BASE_URL}/api/generate",
            json={"model": model, "prompt": prompt, "stream": False},
            timeout=180,
        )
        response.raise_for_status()
        return response.json().get("response", "")
    except requests.exceptions.ConnectionError:
        raise RuntimeError(
            "Ollama に接続できません。\n`ollama serve` を実行してから再試行してください。"
        )
    except requests.exceptions.Timeout:
        raise RuntimeError("Ollama のレスポンスがタイムアウトしました（180秒）。")
    except Exception as e:
        raise RuntimeError(f"Ollama エラー: {e}")


def query_ollama_with_images(prompt: str, image_paths: list[str]) -> str:
    images_b64 = []
    for path in image_paths:
        try:
            with open(path, "rb") as f:
                images_b64.append(base64.b64encode(f.read()).decode("utf-8"))
        except Exception:
            pass
    try:
        response = requests.post(
            f"{OLLAMA_BASE_URL}/api/generate",
            json={
                "model": OLLAMA_VISION_MODEL,
                "prompt": prompt,
                "images": images_b64,
                "stream": False,
            },
            timeout=300,
        )
        response.raise_for_status()
        return response.json().get("response", "")
    except requests.exceptions.ConnectionError:
        raise RuntimeError(
            "Ollama に接続できません。\n`ollama serve` を実行してから再試行してください。"
        )
    except Exception as e:
        raise RuntimeError(f"Ollama (vision) エラー: {e}")


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


def query_anthropic_with_images(prompt: str, image_paths: list[str]) -> str:
    try:
        import anthropic
    except ImportError:
        raise RuntimeError("anthropic パッケージが未インストールです。`pip install anthropic`")

    if not ANTHROPIC_API_KEY:
        raise RuntimeError("ANTHROPIC_API_KEY が設定されていません。")

    content = []
    for path in image_paths:
        try:
            with open(path, "rb") as f:
                data = base64.b64encode(f.read()).decode("utf-8")
            content.append({
                "type": "image",
                "source": {"type": "base64", "media_type": "image/png", "data": data},
            })
        except Exception:
            pass

    content.append({"type": "text", "text": prompt})

    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    message = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=2048,
        messages=[{"role": "user", "content": content}],
    )
    return message.content[0].text


# ── 統合エントリ ──────────────────────────────────────────────────────────────

def query_llm(prompt: str) -> str:
    if USE_ANTHROPIC and ANTHROPIC_API_KEY:
        return query_anthropic(prompt)
    return query_ollama(prompt)


def query_llm_with_images(prompt: str, image_paths: list[str]) -> str:
    if USE_ANTHROPIC and ANTHROPIC_API_KEY:
        return query_anthropic_with_images(prompt, image_paths)
    return query_ollama_with_images(prompt, image_paths)
