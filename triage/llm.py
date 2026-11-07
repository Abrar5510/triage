"""Vultr Serverless Inference client (OpenAI-compatible chat completions). Standard library only."""
import json
import re
import time
import urllib.error
import urllib.request

from . import config


class LLMError(Exception):
    pass


def chat(model: str, messages: list[dict], temperature=0.2, max_tokens=2000) -> str:
    if config.IS_VULTR and not config.INFERENCE_KEY:
        raise LLMError("VULTR_INFERENCE_API_KEY is not set")
    payload = {"model": model, "messages": messages, "temperature": temperature, "max_tokens": max_tokens}
    if config.INFERENCE_EXTRA:
        payload.update(json.loads(config.INFERENCE_EXTRA))
    body = json.dumps(payload).encode()
    headers = {"Content-Type": "application/json"}
    if config.INFERENCE_KEY:
        headers["Authorization"] = f"Bearer {config.INFERENCE_KEY}"
    last = None
    for attempt in range(3):
        req = urllib.request.Request(f"{config.INFERENCE_URL}/chat/completions", data=body, headers=headers)
        try:
            with urllib.request.urlopen(req, timeout=180) as r:
                data = json.load(r)
            content = data["choices"][0]["message"].get("content") or ""
            # Reasoning models may wrap thoughts in <think>…</think>; the answer is what follows.
            content = re.sub(r"<think>.*?</think>", "", content, flags=re.S).strip()
            if not content:
                raise LLMError(f"{model}: empty reply (a reasoning model may have used the whole token budget)")
            return content
        except urllib.error.HTTPError as e:
            last = f"HTTP {e.code}: {e.read()[:300].decode(errors='replace')}"
            if e.code not in (429, 500, 502, 503, 504):
                break
        except (urllib.error.URLError, TimeoutError, KeyError, ValueError) as e:
            last = repr(e)
        time.sleep(2 * (attempt + 1))
    raise LLMError(f"{model}: {last}")


def chat_json(model: str, messages: list[dict], **kw) -> dict:
    """Ask for JSON and parse the first object in the reply (models sometimes add prose or fences)."""
    text = chat(model, messages, **kw)
    m = re.search(r"\{.*\}", text, re.S)
    if not m:
        raise LLMError(f"no JSON object in reply: {text[:200]}")
    return json.loads(m.group(0))


def code_block(text: str) -> str:
    """Extract the Python code from a reply (fenced or bare)."""
    blocks = re.findall(r"```(?:python|py)?\s*\n(.*?)```", text, re.S)
    return max(blocks, key=len).strip() if blocks else text.strip()


def models() -> list[str]:
    req = urllib.request.Request(f"{config.INFERENCE_URL}/models",
                                 headers={"Authorization": f"Bearer {config.INFERENCE_KEY}"} if config.INFERENCE_KEY else {})
    with urllib.request.urlopen(req, timeout=30) as r:
        return [m["id"] for m in json.load(r)["data"]]
