#!/usr/bin/env python3
"""
通用步骤执行器 —— 仅在「用户明确指定了某步用哪个模型」时由宿主 Agent 调用。

不指定模型时，宿主 Agent 应直接按 ../prompts/<step>.md 自己完成该步，不需要本脚本、
不需要任何 API Key。本脚本只负责：把指定步骤的 Prompt 模板填好 → 路由到指定模型 → 流式输出。

用法:
    echo '{"requirement": "..."}' | python3 run_step.py --step intent   --model deepseek/deepseek-v4-flash
    echo '{"requirement": "...", "summary": "..."}' | python3 run_step.py --step outline --model google/gemini-3.1-pro-preview
    echo '{"outline": "...", "search_context": "...", "target_language": "English"}' | python3 run_step.py --step content --model anthropic/claude-opus-4.6
    echo '{"title": "...", "content": "..."}' | python3 run_step.py --step seo_metadata --model ...

多语言：每个目标语言各跑一次 content（改 target_language），从同一份大纲原生生成，而非翻译成稿。

输入: stdin 传 JSON（键见各步占位符）；也可用 --input FILE。
退出码: 0 成功；2 缺对应 API Key；3 未知模型/步骤；1 其他错误。
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

import _client  # 同目录；import 时经 _env 自动加载 .env

_PROMPTS_DIR = Path(__file__).resolve().parent.parent / "prompts"

_STEP_PLACEHOLDERS = {
    "intent":       ["requirement"],
    "summarize":    ["search_results", "target_language"],
    "outline":      ["requirement", "summary", "target_language"],
    "content":      ["outline", "search_context", "target_language"],
    "seo_metadata": ["title", "content"],
}

_NON_STREAMING = {"intent", "seo_metadata"}

_DEFAULTS = {
    "summary": "无相关搜索结果",
    "search_context": "无相关搜索结果",
    "search_results": "无相关搜索结果",
    "target_language": "中文",
}


def _load_prompt(step: str) -> str:
    path = _PROMPTS_DIR / f"{step}.md"
    if not path.exists():
        raise FileNotFoundError(f"找不到 Prompt 模板: {path}")
    text = path.read_text(encoding="utf-8")
    return re.sub(r"<!--\s*META.*?-->\s*", "", text, flags=re.DOTALL).strip()


def _fill(template: str, data: dict, placeholders: list) -> str:
    out = template
    for key in placeholders:
        value = data.get(key)
        if value is None:
            value = _DEFAULTS.get(key, "")
        if not isinstance(value, str):
            value = json.dumps(value, ensure_ascii=False)
        out = out.replace("{{" + key + "}}", value)
    return out


def _extract_json_object(text: str) -> str:
    cleaned = re.sub(r"```json\s*|\s*```", "", text).strip()
    match = re.search(r"\{.*\}", cleaned, re.DOTALL)
    if match:
        try:
            return json.dumps(json.loads(match.group()), ensure_ascii=False, indent=2)
        except json.JSONDecodeError:
            pass
    return cleaned


def main() -> int:
    parser = argparse.ArgumentParser(description="单步骤模型执行器")
    parser.add_argument("--step", required=True, choices=sorted(_STEP_PLACEHOLDERS))
    parser.add_argument("--model", required=True, help="models.yaml 中登记的模型名")
    parser.add_argument("--input", help="输入 JSON 文件（默认从 stdin 读）")
    args = parser.parse_args()

    raw = Path(args.input).read_text(encoding="utf-8") if args.input else sys.stdin.read()
    raw = raw.strip()
    data = json.loads(raw) if raw else {}
    if not isinstance(data, dict):
        print("输入必须是 JSON 对象", file=sys.stderr)
        return 1

    try:
        template = _load_prompt(args.step)
    except FileNotFoundError as exc:
        print(str(exc), file=sys.stderr)
        return 1

    prompt = _fill(template, data, _STEP_PLACEHOLDERS[args.step])

    try:
        if args.step in _NON_STREAMING:
            full = _client.generate_full(prompt, args.model)
            print(_extract_json_object(full))
        else:
            for chunk in _client.generate_stream(prompt, args.model):
                sys.stdout.write(chunk)
                sys.stdout.flush()
            sys.stdout.write("\n")
    except _client.MissingApiKeyError as exc:
        print(str(exc), file=sys.stderr)
        return 2
    except _client.UnknownModelError as exc:
        print(str(exc), file=sys.stderr)
        return 3
    except _client.LLMError as exc:
        print(f"调用失败: {exc}", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
