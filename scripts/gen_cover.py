#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Generic text-to-image against any OpenAI-compatible /v1/images/generations endpoint.

Lets the github-to-wechat skill use an external image model (Agnes, or any
OpenAI-compatible provider) instead of the host tool's built-in generation.

Config, later source wins:
    1. .env in the skill root (recommended)
    2. environment:  IMAGE_API_BASE / IMAGE_API_KEY / IMAGE_MODEL
    3. CLI:          --base-url / --api-key / --model

Response handling covers both common shapes:
    data[0].url      -> downloaded
    data[0].b64_json -> decoded

Usage:
    python gen_cover.py --prompt "..." --out images/cover.png --size 1536x1024
    python gen_cover.py --prompt "..." --base-url https://api.agnes-ai.cn \
        --api-key sk-xxx --model some-image-model
"""
import argparse
import base64
import json
import os
import sys
import urllib.request

TIMEOUT = 180


def load_dotenv(path: str) -> dict:
    """Minimal .env reader: KEY=VALUE per line, # comments and blanks ignored."""
    if not os.path.exists(path):
        return {}
    env = {}
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            env[k.strip()] = v.strip().strip('"').strip("'")
    return env


def dotenv_path() -> str:
    """skill/.env, i.e. one level above scripts/."""
    return os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env")


def apply_proxy_preference(no_proxy: bool):
    """--no-proxy clears proxy env vars and forces a direct connection."""
    if not no_proxy:
        return
    for k in ("HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY",
              "http_proxy", "https_proxy", "all_proxy"):
        os.environ.pop(k, None)
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    urllib.request.install_opener(opener)


def fail(msg: str) -> int:
    print("ERROR: " + msg)
    return 1


def save_b64(b64: str, out: str):
    with open(out, "wb") as f:
        f.write(base64.b64decode(b64))


def save_url(url: str, out: str):
    req = urllib.request.Request(url, headers={"User-Agent": "wechat-cover/1.0"})
    with urllib.request.urlopen(req, timeout=TIMEOUT) as r, open(out, "wb") as f:
        f.write(r.read())


def main() -> int:
    dotenv = load_dotenv(dotenv_path())
    ap = argparse.ArgumentParser(description="text-to-image via OpenAI-compatible API")
    ap.add_argument("--prompt", required=True)
    ap.add_argument("--out", required=True, help="output PNG path")
    ap.add_argument("--size", default="1536x1024", help="e.g. 1536x1024, or 2K on Agnes")
    ap.add_argument("--base-url", default=os.environ.get("IMAGE_API_BASE")
                    or dotenv.get("IMAGE_API_BASE", "https://api.agnes-ai.cn"))
    ap.add_argument("--api-key", default=os.environ.get("IMAGE_API_KEY")
                    or os.environ.get("AGNES_API_KEY") or dotenv.get("IMAGE_API_KEY"))
    ap.add_argument("--model", default=os.environ.get("IMAGE_MODEL")
                    or dotenv.get("IMAGE_MODEL", ""))
    ap.add_argument("--quality", default="high", help="passed through if provider supports it")
    ap.add_argument("--no-proxy", action="store_true",
                    help="force direct connection; for local proxies (Clash etc.) that are down")
    args = ap.parse_args()

    apply_proxy_preference(args.no_proxy)

    if not args.api_key:
        return fail("缺少 API key。首次使用请执行：\n"
                    "  cp .env.example .env   (Windows: copy .env.example .env)\n"
                    "  然后填 IMAGE_API_KEY。也可用环境变量 IMAGE_API_KEY 或 --api-key 传入。")
    if any(ord(c) > 127 for c in args.api_key):
        return fail("API key 含非 ASCII 字符。header 只能 latin-1 编码，"
                    "检查 .env 里的 key 是不是还没替换掉占位符")
    if not args.model:
        print("set IMAGE_MODEL, or pass --model (e.g. the provider's image model id)")
        return 1

    endpoint = args.base_url.rstrip("/") + "/v1/images/generations"
    payload = {"model": args.model, "prompt": args.prompt, "n": 1, "size": args.size}
    body = json.dumps(payload).encode("utf-8")

    req = urllib.request.Request(
        endpoint, data=body, method="POST",
        headers={
            "Authorization": "Bearer " + args.api_key,
            "Content-Type": "application/json",
            "User-Agent": "wechat-cover/1.0",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
            resp = json.loads(r.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        detail = e.read().decode("utf-8", "replace")[:500]
        hint = ""
        if e.code == 400:
            hint = ("\nsize 无效时先怀疑档位名：Agnes 的 size 只收 1K/2K/3K/4K，"
                    "不收 1536x1024 这类像素值（视频接口同理）。加 --size 2K 重试。")
        return fail("HTTP %s from %s%s\n%s" % (e.code, endpoint, hint, detail))
    except urllib.error.URLError as e:
        hint = ""
        proxy = (os.environ.get("HTTPS_PROXY") or os.environ.get("HTTP_PROXY")
                 or os.environ.get("https_proxy") or os.environ.get("http_proxy"))
        if proxy:
            hint = "\n本地代理 %s 可能没开。加 --no-proxy 强制直连，或把代理服务启动。" % proxy
        return fail("connection failed: %s%s" % (e.reason, hint))

    items = resp.get("data") or []
    if not items:
        return fail("no data in response: " + json.dumps(resp)[:300])

    item = items[0]
    os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
    if item.get("b64_json"):
        save_b64(item["b64_json"], args.out)
    elif item.get("url"):
        save_url(item["url"], args.out)
    else:
        return fail("neither b64_json nor url in first item: " + json.dumps(item)[:300])

    size_kb = os.path.getsize(args.out) // 1024
    print("OK -> %s (%d KB)" % (args.out, size_kb))
    return 0


if __name__ == "__main__":
    sys.exit(main())
