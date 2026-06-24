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
成本: 加 --usage（默认关）时，跑完向 stderr 输出一行 `[[USAGE]] {...}`，含 token 用量与
      cost_usd；cost 仅 OpenRouter 模型提供。不加该标志则公开行为与旧版完全一致。
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


def _emit_usage(step: str, model: str, usage: dict) -> None:
    """把本步 OpenRouter 用量/成本以 [[USAGE]] 前缀打到 stderr（不污染 stdout 正文）。

    调用方（如发布技能的宿主 Agent）收集所有 [[USAGE]] 行即可汇总成本明细。
    cost_usd 来自 OpenRouter 的 usage.cost（美元）；未开启用量或非 OpenRouter 时为空。
    """
    if not usage:
        return
    info = {
        "step": step,
        "model": model,
        "prompt_tokens": usage.get("prompt_tokens"),
        "completion_tokens": usage.get("completion_tokens"),
        "total_tokens": usage.get("total_tokens"),
        "cost_usd": usage.get("cost"),
    }
    print("[[USAGE]] " + json.dumps(info, ensure_ascii=False), file=sys.stderr)


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
    parser.add_argument("--usage", action="store_true",
                        help="跑完向 stderr 输出一行 [[USAGE]] 用量/成本 JSON（默认关；cost 仅 OpenRouter）")
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

    # 默认不收集用量（usage=None → 不向 OpenRouter 请求 usage、不打印），公开行为零变化；
    # 仅当显式 --usage 时才传入收集容器并在末尾汇报。
    usage = {} if args.usage else None
    try:
        if args.step in _NON_STREAMING:
            full = _client.generate_full(prompt, args.model, usage=usage)
            print(_extract_json_object(full))
        else:
            for chunk in _client.generate_stream(prompt, args.model, usage=usage):
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

    if args.usage:
        _emit_usage(args.step, args.model, usage)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
