"""
多供应商 LLM 流式客户端（脱离 Web，仅在「用户明确指定某步用哪个模型」时被 run_step 调用）。

设计要点：
- 零第三方依赖：HTTP 用标准库 urllib；models.yaml 用内置极简 YAML 子集解析器
  （若环境恰好装了 PyYAML 则优先用它），便于丢进任意 Agent 环境。
- import 时经 _env 自动加载仓库根 .env；API Key 一律从环境变量读取（models.yaml 只声明变量名）。
- 缺 Key 时抛 MissingApiKeyError，由 run_step.py 打印「该设哪个变量」并非零退出，不重试。
"""

from __future__ import annotations

import json
import os
import re
import urllib.error
import urllib.request
from pathlib import Path
from typing import Dict, Iterator, List, Optional

import _env  # noqa: F401  导入即自动加载 .env

_CATALOG_PATH = Path(__file__).resolve().parent / "models.yaml"


class LLMError(Exception):
    """通用 LLM 调用错误。"""


class UnknownModelError(LLMError):
    """models.yaml 中找不到该模型。"""


class MissingApiKeyError(LLMError):
    """模型所属 provider 需要的环境变量未设置。"""

    def __init__(self, model: str, provider: str, key_env: str):
        self.model = model
        self.provider = provider
        self.key_env = key_env
        super().__init__(
            f"模型 {model} 由 {provider} 提供，需要环境变量 {key_env}，但未检测到；"
            f"请把它写入仓库根 .env（可运行 python3 setup.py {key_env}=...）后重试。"
        )


# ----------------------------------------------------------------------------
# 模型目录
# ----------------------------------------------------------------------------

def load_catalog(path: Optional[Path] = None) -> dict:
    catalog_path = path or _CATALOG_PATH
    text = Path(catalog_path).read_text(encoding="utf-8")
    try:
        import yaml  # PyYAML 若存在则优先用，更稳健
        return yaml.safe_load(text) or {}
    except ImportError:
        return _parse_simple_yaml(text)


def available_models(catalog: Optional[dict] = None) -> List[str]:
    catalog = catalog or load_catalog()
    out: List[str] = []
    for prov in (catalog.get("providers") or {}).values():
        out.extend(prov.get("models", []))
    return out


def resolve_model(model_name: str, catalog: Optional[dict] = None) -> Dict:
    """按模型名定位 provider，返回调用所需的配置（含从 env 读出的 api_key）。"""
    catalog = catalog or load_catalog()
    for provider_name, prov in (catalog.get("providers") or {}).items():
        if model_name in prov.get("models", []):
            key_env = prov.get("key_env", "")
            api_key = os.environ.get(key_env, "").strip()
            if not api_key:
                raise MissingApiKeyError(model_name, provider_name, key_env)
            return {
                "provider": provider_name,
                "model": model_name,
                "endpoint": prov["endpoint"].rstrip("/"),
                "protocol": prov.get("protocol", "openai"),
                "api_key": api_key,
                "proxy": bool(prov.get("proxy", False)),
            }
    raise UnknownModelError(
        f"未知模型 {model_name!r}。可用模型: {', '.join(available_models(catalog)) or '(空)'}"
    )


# -- 内置极简 YAML 子集解析器（仅支持本目录 models.yaml 的结构：嵌套 map + 标量 list）--

def _strip_inline_comment(s: str) -> str:
    out: List[str] = []
    quote = None
    prev = ""
    for ch in s:
        if quote:
            out.append(ch)
            if ch == quote:
                quote = None
        elif ch in ('"', "'"):
            quote = ch
            out.append(ch)
        elif ch == "#" and (prev == "" or prev in " \t"):
            break
        else:
            out.append(ch)
        prev = ch
    return "".join(out)


def _coerce_scalar(v: str):
    v = v.strip()
    if len(v) >= 2 and v[0] == v[-1] and v[0] in ('"', "'"):
        return v[1:-1]
    low = v.lower()
    if low == "true":
        return True
    if low == "false":
        return False
    if low in ("null", "~", ""):
        return None
    if re.fullmatch(r"-?\d+", v):
        return int(v)
    return v


def _parse_simple_yaml(text: str) -> dict:
    root: dict = {}
    stack = [{"indent": -1, "obj": root, "kind": "map"}]
    pending = None  # {"indent": int, "map": dict, "key": str}

    for raw in text.splitlines():
        line = _strip_inline_comment(raw)
        if not line.strip():
            continue
        indent = len(line) - len(line.lstrip(" "))
        content = line.strip()

        if pending is not None and indent > pending["indent"]:
            is_list = content.startswith("- ") or content == "-"
            new_obj: object = [] if is_list else {}
            pending["map"][pending["key"]] = new_obj
            stack.append({"indent": indent, "obj": new_obj,
                          "kind": "list" if is_list else "map"})
        pending = None

        while len(stack) > 1 and indent < stack[-1]["indent"]:
            stack.pop()
        frame = stack[-1]

        if content.startswith("- ") or content == "-":
            item = content[2:].strip() if content.startswith("- ") else ""
            if frame["kind"] == "list":
                frame["obj"].append(_coerce_scalar(item))
            continue

        if ":" not in content:
            continue
        key, _, val = content.partition(":")
        key, val = key.strip(), val.strip()
        if frame["kind"] != "map":
            continue
        if val == "":
            frame["obj"].setdefault(key, None)
            pending = {"indent": indent, "map": frame["obj"], "key": key}
        else:
            frame["obj"][key] = _coerce_scalar(val)

    return root


# ----------------------------------------------------------------------------
# HTTP（标准库 urllib，支持可选 HTTP 代理 + SSE 流式解析）
# ----------------------------------------------------------------------------

def _build_opener(use_proxy: bool) -> urllib.request.OpenerDirector:
    proxy_url = os.environ.get("HTTP_PROXY", "").strip()
    if use_proxy and proxy_url:
        handler = urllib.request.ProxyHandler({"http": proxy_url, "https": proxy_url})
    else:
        handler = urllib.request.ProxyHandler({})  # 显式禁用环境代理
    return urllib.request.build_opener(handler)


def _post_stream(url: str, headers: Dict[str, str], payload: dict, use_proxy: bool) -> Iterator[str]:
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers=headers, method="POST")
    opener = _build_opener(use_proxy)
    try:
        with opener.open(req, timeout=120) as resp:
            for raw in resp:
                yield raw.decode("utf-8", errors="replace").rstrip("\r\n")
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")[:500]
        raise LLMError(f"LLM API 返回错误 (HTTP {exc.code}): {body}") from exc
    except urllib.error.URLError as exc:
        raise LLMError(f"无法连接 LLM API: {exc.reason}") from exc


def _openai_stream(prompt: str, cfg: Dict, usage: Optional[Dict] = None) -> Iterator[str]:
    headers = {
        "Authorization": f"Bearer {cfg['api_key']}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": cfg["model"],
        "messages": [{"role": "user", "content": prompt}],
        "stream": True,
        "temperature": 0.7,
    }
    # OpenRouter「用量计费」扩展：在响应（含流式最后一个 chunk）里回传 token 用量与成本(USD)。
    # 仅在调用方要 usage 且端点是 OpenRouter 时开启，避免影响其它 OpenAI 兼容端点。
    if usage is not None and "openrouter" in cfg["endpoint"]:
        payload["usage"] = {"include": True}
    for line in _post_stream(f"{cfg['endpoint']}/chat/completions", headers, payload, cfg["proxy"]):
        if not line.startswith("data: "):
            continue
        payload_str = line[6:]
        if payload_str.strip() == "[DONE]":
            break
        try:
            chunk = json.loads(payload_str)
        except json.JSONDecodeError:
            continue
        if usage is not None and isinstance(chunk.get("usage"), dict):
            usage.update(chunk["usage"])  # 末尾 chunk 携带最终用量+cost
        choices = chunk.get("choices") or []
        if choices:
            content = (choices[0].get("delta") or {}).get("content")
            if content:
                yield content


def _claude_stream(prompt: str, cfg: Dict) -> Iterator[str]:
    headers = {
        "x-api-key": cfg["api_key"],
        "anthropic-version": "2023-06-01",
        "Content-Type": "application/json",
    }
    payload = {
        "model": cfg["model"],
        "messages": [{"role": "user", "content": prompt}],
        "stream": True,
        "max_tokens": 4096,
    }
    for line in _post_stream(f"{cfg['endpoint']}/v1/messages", headers, payload, cfg["proxy"]):
        if not line.startswith("data: "):
            continue
        try:
            chunk = json.loads(line[6:])
        except json.JSONDecodeError:
            continue
        if chunk.get("type") == "content_block_delta":
            text = (chunk.get("delta") or {}).get("text")
            if text:
                yield text


def generate_stream(prompt: str, model_name: str, catalog: Optional[dict] = None,
                    usage: Optional[Dict] = None) -> Iterator[str]:
    cfg = resolve_model(model_name, catalog)
    if cfg["protocol"] == "claude":
        yield from _claude_stream(prompt, cfg)  # claude 原生协议（本技能未用）不回传 cost
    else:
        yield from _openai_stream(prompt, cfg, usage=usage)


def generate_full(prompt: str, model_name: str, catalog: Optional[dict] = None,
                  usage: Optional[Dict] = None) -> str:
    return "".join(generate_stream(prompt, model_name, catalog, usage=usage))
