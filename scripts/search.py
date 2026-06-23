#!/usr/bin/env python3
"""
联网搜索（Tavily）—— 仅标准库 urllib，TAVILY_API_KEY 从仓库根 .env / 环境变量读取。

默认建议优先用宿主 Agent 自带的 web 搜索；本脚本是「设置了 TAVILY_API_KEY 时」的可选后端，
完整保留原逻辑：search_depth=advanced、每词最多 3 条、跨词 URL 去重、结果格式化。

用法:
    echo '{"keywords": ["kw1", "kw2"]}' | python3 search.py          # 输出格式化文本
    echo '{"keywords": ["kw1"]}'        | python3 search.py --json    # 输出结构化 JSON
    python3 search.py --keywords "kw1" "kw2"

退出码: 0 成功；2 缺 TAVILY_API_KEY；1 其他错误。
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.request
from typing import List

import _env  # noqa: F401  导入即自动加载 .env

_TAVILY_ENDPOINT = "https://api.tavily.com/search"
_NOISE_KEYWORDS = ("Login", "Menu", "Sign up", "Copyright")


class TavilyKeyMissing(Exception):
    pass


def _tavily_search_one(api_key: str, query: str, max_results: int = 3) -> list:
    payload = json.dumps({
        "api_key": api_key,
        "query": query,
        "search_depth": "advanced",
        "include_raw_content": False,
        "max_results": max_results,
    }).encode("utf-8")
    req = urllib.request.Request(
        _TAVILY_ENDPOINT, data=payload,
        headers={"Content-Type": "application/json"}, method="POST",
    )
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    with opener.open(req, timeout=60) as resp:
        body = json.loads(resp.read().decode("utf-8", errors="replace"))
    return body.get("results", []) or []


def search_multi_query(queries: List[str], max_results: int = 3) -> list:
    api_key = os.environ.get("TAVILY_API_KEY", "").strip()
    if not api_key:
        raise TavilyKeyMissing(
            "未检测到 TAVILY_API_KEY；如需 Tavily 搜索请把它写入仓库根 .env "
            "（python3 setup.py TAVILY_API_KEY=...），否则请改用宿主 Agent 自带的联网搜索。"
        )

    all_results: list = []
    seen_urls: set = set()
    for q in queries:
        try:
            for result in _tavily_search_one(api_key, q, max_results):
                url = result.get("url")
                if url and url not in seen_urls:
                    seen_urls.add(url)
                    all_results.append(result)
        except (urllib.error.HTTPError, urllib.error.URLError) as exc:
            print(f"[WARN] Tavily 搜索 {q!r} 失败: {exc}", file=sys.stderr)
            continue
    return all_results


def format_search_results(results: list) -> str:
    if not results:
        return "无相关搜索结果"
    parts: list = []
    idx = 1
    for result in results:
        title = result.get("title", "No Title")
        url = result.get("url", "")
        content = result.get("content", "") or ""
        if len(content) < 50 and any(kw in content for kw in _NOISE_KEYWORDS):
            continue
        summary = content[:1500] + "..." if len(content) > 1500 else content
        parts.append(f"Source [{idx}]: {title}\nURL: {url}\nContent: {summary}")
        idx += 1
    return "\n\n".join(parts) if parts else "无相关搜索结果"


def _read_keywords(args) -> List[str]:
    if args.keywords:
        return args.keywords
    raw = sys.stdin.read().strip()
    if not raw:
        return []
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return [line.strip() for line in raw.splitlines() if line.strip()]
    if isinstance(data, list):
        return [str(x) for x in data]
    return [str(x) for x in (data.get("keywords") or [])]


def main() -> int:
    parser = argparse.ArgumentParser(description="Tavily 多关键词搜索")
    parser.add_argument("--keywords", nargs="*", help="直接传入关键词（否则从 stdin 读 JSON）")
    parser.add_argument("--json", action="store_true", help="输出结构化 JSON 而非格式化文本")
    parser.add_argument("--max-results", type=int, default=3, help="每关键词最大结果数（默认 3）")
    args = parser.parse_args()

    keywords = _read_keywords(args)
    if not keywords:
        print("无关键词输入", file=sys.stderr)
        return 1

    try:
        results = search_multi_query(keywords, args.max_results)
    except TavilyKeyMissing as exc:
        print(str(exc), file=sys.stderr)
        return 2

    if args.json:
        slim = [
            {"title": r.get("title", ""), "url": r.get("url", ""),
             "content": (r.get("content", "") or "")[:1500]}
            for r in results
        ]
        print(json.dumps(slim, ensure_ascii=False, indent=2))
    else:
        print(format_search_results(results))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
