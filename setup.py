#!/usr/bin/env python3
"""
配置助手 —— 把 API Key 写入本仓库根目录的 .env（gitignored），脚本 import 时自动加载。

重要：本技能默认由宿主 Agent 自己的模型写作，**无需任何 Key**。只有当你想让某一步
用某个具体第三方模型（如让大纲用 gemini）、或启用 Tavily 联网搜索时，才需要配置对应 Key。

用法:
    # 非交互（适合 AI Agent）——传 KEY=VALUE，可多个：
    python3 setup.py OPENROUTER_API_KEY=sk-or-xxx TAVILY_API_KEY=tvly-xxx

    # 交互式向导（逐个询问，回车跳过）：
    python3 setup.py

已存在的其他键不会被清空，只更新你这次提供的键。
"""

from __future__ import annotations

import sys
from pathlib import Path

ENV_PATH = Path(__file__).resolve().parent / ".env"

# 已知可配置的变量及说明（顺序即向导询问顺序）
KNOWN_KEYS = [
    ("OPENROUTER_API_KEY", "OpenRouter —— 一个 Key 覆盖所有第三方模型（deepseek/qwen/kimi/gemini/claude…）"),
    ("TAVILY_API_KEY", "Tavily 联网搜索（可选）"),
    ("HTTP_PROXY", "HTTP 代理（可选，OpenRouter 走它）"),
]
_KNOWN_NAMES = {k for k, _ in KNOWN_KEYS}


def _read_existing() -> dict:
    data: dict = {}
    if ENV_PATH.is_file():
        for raw in ENV_PATH.read_text(encoding="utf-8").splitlines():
            line = raw.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            data[k.strip()] = v.strip()
    return data


def _write(data: dict) -> None:
    lines = ["# sinkey-seo-writer 配置 —— 本文件含密钥，已被 .gitignore 忽略，请勿提交。", ""]
    for k, _desc in KNOWN_KEYS:
        if k in data and data[k]:
            lines.append(f"{k}={data[k]}")
    # 保留用户自定义的未知键
    for k, v in data.items():
        if k not in _KNOWN_NAMES and v:
            lines.append(f"{k}={v}")
    ENV_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _parse_args(argv: list) -> dict:
    out: dict = {}
    for arg in argv:
        if "=" not in arg:
            print(f"忽略无效参数（应为 KEY=VALUE）: {arg}", file=sys.stderr)
            continue
        k, v = arg.split("=", 1)
        out[k.strip()] = v.strip()
    return out


def _interactive() -> dict:
    print("交互式配置（回车跳过该项；所有项都可留空 —— 默认用宿主 Agent 模型，无需任何 Key）\n")
    out: dict = {}
    for k, desc in KNOWN_KEYS:
        val = input(f"  {k}  —— {desc}\n  > ").strip()
        if val:
            out[k] = val
    return out


def main() -> int:
    updates = _parse_args(sys.argv[1:]) if len(sys.argv) > 1 else _interactive()
    if not updates:
        print("未提供任何键；未改动 .env。")
        return 0

    data = _read_existing()
    data.update(updates)
    _write(data)

    print(f"\n✅ 已写入 {ENV_PATH}")
    for k in updates:
        masked = (updates[k][:6] + "…") if len(updates[k]) > 6 else "✓"
        print(f"   {k} = {masked}")
    print("\n脚本会在运行时自动加载该 .env，无需 export。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
