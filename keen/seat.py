"""The GLM seat. The bytes it returns are the answer.

No second pass. No refusal list. No retry until the words change. A key stays
in the environment and is never written into a lap.
"""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from urllib.parse import urlparse

DEFAULT_URL = "https://api.z.ai/api/paas/v4/chat/completions"
DEFAULT_MODEL = "glm-5.3"
_LOCAL = {"127.0.0.1", "localhost", "::1"}


def glm_url() -> str:
    return (os.environ.get("KEEN_GLM_URL") or DEFAULT_URL).strip()


def glm_key() -> str:
    return (os.environ.get("KEEN_GLM_KEY") or os.environ.get("ZHIPU_API_KEY") or "").strip()


def glm_model() -> str:
    return (os.environ.get("KEEN_GLM_MODEL") or DEFAULT_MODEL).strip()


def public_host(url: str) -> str:
    """Host and port only. Userinfo and the path stay out of the card."""
    parsed = urlparse(url or "")
    host = parsed.hostname or ""
    if parsed.port:
        return f"{host}:{parsed.port}"
    return host


def is_local(url: str) -> bool:
    return (urlparse(url or "").hostname or "").lower() in _LOCAL


def needs_key(url: str, key: str) -> str | None:
    """Why this call must not leave the machine. None means it may leave."""
    if is_local(url):
        return None
    if not key:
        return "glm has no key"
    return None


def complete(messages: list, *, url: str, key: str, model: str, timeout: float = 45,
             opener=None) -> str:
    """POST one chat completion and return the content exactly."""
    opener = opener or urllib.request.urlopen
    body = json.dumps({
        "model": model,
        "messages": messages,
        "temperature": 0.6,
        "max_tokens": 2048,
    }).encode("utf-8")
    headers = {"Content-Type": "application/json", "Accept": "application/json"}
    if key:
        headers["Authorization"] = "Bearer " + key
    req = urllib.request.Request(url, data=body, headers=headers, method="POST")
    try:
        with opener(req, timeout=timeout) as resp:
            payload = resp.read().decode("utf-8", "replace")
    except urllib.error.HTTPError:
        return "seat dark: glm"
    except Exception:
        return "seat dark: glm"
    try:
        data = json.loads(payload)
        content = data["choices"][0]["message"]["content"]
    except (json.JSONDecodeError, KeyError, IndexError, TypeError):
        return "seat dark: glm"
    if content is None:
        return ""
    return str(content)


def live_glm(messages: list, opener=None) -> str:
    url = glm_url()
    key = glm_key()
    blocked = needs_key(url, key)
    if blocked:
        return "seat dark: " + blocked
    return complete(
        messages,
        url=url,
        key=key,
        model=glm_model(),
        opener=opener,
    )


def make_fast_once(opener=None):
    """A fast local seat for votes, or None when KEEN_FAST_URL is unset."""
    url = (os.environ.get("KEEN_FAST_URL") or "").strip()
    if not url:
        return None
    model = (os.environ.get("KEEN_FAST_MODEL") or "local").strip()
    key = (os.environ.get("KEEN_FAST_KEY") or "").strip()

    def once(text: str, options: list[str]) -> str:
        prompt = (
            "Classify the text into EXACTLY ONE of these labels: "
            + ", ".join(options)
            + "\nReply with ONLY the label. If none fits, reply NONE.\n\nTEXT:\n"
            + str(text)[:1200]
        )
        return complete(
            [{"role": "user", "content": prompt}],
            url=url,
            key=key,
            model=model,
            timeout=8,
            opener=opener,
        )

    return once


def seats_text() -> str:
    url = glm_url()
    key = glm_key()
    if is_local(url):
        glm_light = "local"
    elif key:
        glm_light = "key"
    else:
        glm_light = "no key"
    fast = (os.environ.get("KEEN_FAST_URL") or "").strip()
    fast_light = public_host(fast) if fast else "no url"
    return (
        f"glm    {glm_light:<6}  {public_host(url)}\n"
        f"model  {glm_model()}\n"
        f"fast   {fast_light}"
    )
