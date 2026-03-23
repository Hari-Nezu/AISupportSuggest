import requests

from config import (
    ANTHROPIC_API_KEY,
    OLLAMA_BASE_URL,
    OLLAMA_MODEL,
    USE_ANTHROPIC,
)


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


def query_anthropic(prompt: str) -> str:
    try:
        import anthropic
    except ImportError:
        raise RuntimeError("anthropic パッケージが未インストールです。`pip install anthropic` を実行してください。")

    if not ANTHROPIC_API_KEY:
        raise RuntimeError("ANTHROPIC_API_KEY が設定されていません。")

    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    message = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=2048,
        messages=[{"role": "user", "content": prompt}],
    )
    return message.content[0].text


def query_llm(prompt: str) -> str:
    if USE_ANTHROPIC and ANTHROPIC_API_KEY:
        return query_anthropic(prompt)
    return query_ollama(prompt)


def list_ollama_models() -> list[str]:
    try:
        response = requests.get(f"{OLLAMA_BASE_URL}/api/tags", timeout=5)
        response.raise_for_status()
        models = response.json().get("models", [])
        return [m["name"] for m in models]
    except Exception:
        return []
