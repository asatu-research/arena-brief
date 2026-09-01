"""Klien LLM: Grok (xAI), DeepSeek, Mistral — via HTTP sederhana."""
import httpx

from app.config import get_settings

settings = get_settings()

ENDPOINTS = {
    "grok": "https://api.x.ai/v1/chat/completions",
    "deepseek": "https://api.deepseek.com/chat/completions",
    "mistral": "https://api.mistral.ai/v1/chat/completions",
}


def _key_for(provider: str) -> str:
    if provider == "grok":
        return settings.grok_api_key
    if provider == "deepseek":
        return settings.deepseek_api_key
    if provider == "mistral":
        return settings.mistral_api_key
    return ""


async def chat(provider: str, model: str, messages: list[dict], json_mode: bool = False, max_tokens: int = 3000) -> str:
    key = _key_for(provider)
    if not key:
        raise RuntimeError(f"API key untuk {provider} belum diisi.")
    payload = {
        "model": model,
        "messages": messages,
        "max_tokens": max_tokens,
    }
    if json_mode:
        payload["response_format"] = {"type": "json_object"}
    async with httpx.AsyncClient(timeout=180.0) as client:
        resp = await client.post(
            ENDPOINTS[provider],
            headers={"Authorization": f"Bearer {key}"},
            json=payload,
        )
        resp.raise_for_status()
        data = resp.json()
        return data["choices"][0]["message"]["content"]


async def chat_json(provider: str, model: str, messages: list[dict], max_tokens: int = 4000) -> dict:
    content = await chat(provider, model, messages, json_mode=True, max_tokens=max_tokens)
    import json
    try:
        return json.loads(content)
    except json.JSONDecodeError:
        # kadang model membungkus json dalam ```json ... ```
        import re
        m = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", content, re.DOTALL)
        if m:
            return json.loads(m.group(1))
        raise
