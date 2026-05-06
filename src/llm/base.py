"""统一 LLM 客户端封装"""

import os
import json
import hashlib
from pathlib import Path

import httpx
from openai import OpenAI

BASE_DIR = Path(__file__).parent.parent.parent
CACHE_DIR = BASE_DIR / "cache"


def get_client() -> OpenAI:
    api_key = os.getenv("LLM_API_KEY", "")
    base_url = os.getenv("LLM_BASE_URL", "https://token-plan-cn.xiaomimimo.com/v1")
    return OpenAI(
        api_key=api_key,
        base_url=base_url,
        http_client=httpx.Client(verify=False, trust_env=False),
    )


def _cache_key(prompt: str) -> str:
    return hashlib.md5(prompt.encode()).hexdigest()[:12]


def chat(system_prompt: str, user_prompt: str, *, use_cache: bool = True) -> str:
    model = os.getenv("LLM_MODEL", "mimo-v2.5-pro")
    full_prompt = f"{system_prompt}\n{user_prompt}"

    # 检查缓存
    if use_cache:
        CACHE_DIR.mkdir(parents=True, exist_ok=True)
        cache_file = CACHE_DIR / f"{_cache_key(full_prompt)}.json"
        if cache_file.exists():
            cached = json.loads(cache_file.read_text())
            return cached["response"]

    client = get_client()
    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        max_tokens=4000,
        temperature=0.3,
    )
    result = response.choices[0].message.content

    # 写入缓存
    if use_cache:
        CACHE_DIR.mkdir(parents=True, exist_ok=True)
        cache_file = CACHE_DIR / f"{_cache_key(full_prompt)}.json"
        cache_file.write_text(json.dumps({"prompt": full_prompt[:200], "response": result}, ensure_ascii=False))

    return result
