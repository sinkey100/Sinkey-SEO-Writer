---
name: sinkey/seo-writer
description: 搜索增强的 SEO 长文写作流水线，把「意图分析（定语言/地区）→ 联网调研 → 总结 → 大纲 → 正文 → SEO 元数据」编排成一次写作；支持一条龙全自动、单步自定义、从指定步骤重做并继续。多语言无需翻译——用户用什么语言写意图，就用该语言所在地区从头做一篇全新本地文章（搜索词/调研/大纲/正文全程该地区语言）。每一步默认由宿主 Agent 的模型完成（零配置、零 API Key），也可在自然语言里为某一步指定具体第三方模型（如大纲用 gemini、正文用 opus）。Use when the user wants to 写一篇SEO文章 / 写博客 / 写长文 / generate an article, 生成大纲 / outline, 写正文 / draft / write content, 写英文/日文等多语言版本 / multilingual article (e.g. 写美国市场/for US/日本語版), 生成SEO元数据 / slug / 标题 / 描述 / 关键词 / SEO metadata, 带联网调研写稿 / web-researched writing, 一键生成 / 一条龙 / one-shot generation, 单步执行 / run one step, 回到/从某一步重做并继续 / resume from a step. 正文遵循 E-E-A-T + 费曼降维表达。Intent synonyms: SEO article writing, blog post, long-form content, intent analysis, keyword research, web research, outline generation, article drafting, native multilingual / per-locale article, SEO metadata, 内容生成, 选题大纲, 正文撰写, 多语言本地文章, 重写某一步.
---

# SEO Writer（SEO 长文写作流水线）

把「意图分析（定语言/地区）→ 联网调研 → 总结 → 大纲 → 正文 →（可选 SEO 元数据）」编排成一次写作。
完整 Prompt 在 [`prompts/`](prompts/)，多模型脚本在 [`scripts/`](scripts/)。

> **多语言默认走「统一大纲 + 各地区原生正文」（推荐，适合资讯/教程/对比等多语言站）：**
> 用主语言跑一遍 意图→调研→总结→大纲，产出一份**统一大纲**（跨语言的结构+事实骨架）；再为每个目标语言各跑一次 `content`（换 `target_language`），每次**原生用该语言写作 + 本地化关键词**。结构/章节/观点跨语言一致，语言与搜索词彻底本地——无需翻译。
>
> **进阶（某市场需要完全不同的调研角度/选题，如各地区竞品不同）**：改用「从意图各自独立」——整条线按地区各跑一遍（即从 intent 步换语言重跑）。本地化最深，但各语言版本可能叙事不同、成本最高。
（以下命令里的路径都相对本技能文件夹根目录；如当前目录不在此，请先 `cd` 到本技能目录。）

## 模型选择约定（核心 —— 务必遵守）

每一步都有两种执行方式，**默认走第一种**：

1. **默认：你（宿主 Agent 的模型）亲自写。** 不需要任何 API Key。
   读取该步的 `prompts/<step>.md`，把里面的 `{{占位符}}` 用实际内容替换后，**自己**产出结果。

2. **委托：仅当用户明确为某步指定了具体模型时**（如「大纲用 `google/gemini-3.1-pro-preview`、正文用 `deepseek/deepseek-v4-pro`」），把该步交给脚本执行：
   ```bash
   echo '<输入JSON>' | python3 scripts/run_step.py --step <step> --model <模型名>
   ```
   - 所有第三方模型统一经 **OpenRouter** 调用，只需一个 `OPENROUTER_API_KEY`。脚本按 [`scripts/models.yaml`](scripts/models.yaml) 把模型 ID 解析成调用方式，并从仓库根 `.env` / 环境变量读 Key。
   - **若 `OPENROUTER_API_KEY` 未设置，脚本会报错指明该配它**：把错误**原样转达用户**，提示其运行 `python3 setup.py OPENROUTER_API_KEY=...` 后重试，**不要自己换别的模型、也不要重试**。
   - 用户没点名某步的模型，那一步就继续用「默认：你亲自写」，不要主动调脚本。

> 可用模型 ID（OpenRouter 形式，如 `deepseek/deepseek-v4-pro`）与每步推荐模型见 `scripts/models.yaml`。配置 Key 见 **配置** 一节。

## 三种用法

### A. 一条龙（全自动，主语言）
用户说「写一篇关于 X 的 SEO 文章」时，按 **流水线** 顺序一路跑到底，产出**主语言**版本（语言/地区由 intent 步确定：用户书写语言即默认地区；点名地区时以用户为准）。
每步产出建议落盘（如 `outline.md`、`article.md`）。要其它语言版本 → 见 **多语言（统一大纲）**。

### B. 多语言（统一大纲，推荐）
先跑 A 拿到**统一大纲**（主语言），再为每个目标语言**各跑一次 `content`**（`target_language` 换成该语言），每次原生写作 + 本地化关键词：
```bash
echo '{"outline": <统一大纲>, "search_context": <总结>, "target_language": "English"}' | python3 scripts/run_step.py --step content --model anthropic/claude-opus-4.6
```
结构/章节/观点跨语言一致；可按市场价值分级用模型（核心市场 opus，长尾语言便宜模型）。

### C. 单步 / 从指定步骤重做并继续
- **单步**：「只生成大纲」「只写正文」「给这篇生成 SEO 元数据」→ 只跑那一步。
- **重做并续跑**：「大纲第 3 点改…，从大纲重新来，后面接着写正文」→ 从该步重跑后续；改了大纲后记得重跑各语言 content。
- **进阶（从意图各自独立）**：某市场要完全不同调研角度/选题时，从 **intent 步** 换语言重跑整条线（最深本地化、成本最高）。

## 流水线

| # | 步骤 | prompt | 输入(JSON 键) | 产出 |
|---|---|---|---|---|
| 1 | 意图分析 | [intent.md](prompts/intent.md) | `requirement` | `{language, keywords[]}`：确定目标语言/地区 + 该地区 3 个真实搜索词 |
| 2 | 联网调研（可选，双通道）| — | keywords(已本地化) | 该地区相关搜索结果(去重+格式化) |
| 3 | 总结 | [summarize.md](prompts/summarize.md) | `search_results`,`target_language` | 结构化总结 = `summary`/`search_context`（用该语言） |
| 4 | 大纲 | [outline.md](prompts/outline.md) | `requirement`,`summary`,`target_language` | 5 模块 Markdown 大纲（该语言 + 该地区关键词） |
| 5 | 正文 | [content.md](prompts/content.md) | `outline`,`search_context`,`target_language` | 1500-2000 字长文（该语言） |
| · | SEO 元数据（可选）| [seo_metadata.md](prompts/seo_metadata.md) | `title`,`content` | slug/标题/描述/关键词 JSON（与正文同语言） |

> `target_language` = intent 步确定的**主语言**，用于 summarize/outline（跑一次）。**content 步按需换语言**：多语言站里同一大纲为每个目标语言各跑一次 content。

**Step 2 联网调研（双通道，按优先级，任一不可用就降级并一句话告知用户）**：
1. **宿主 web 搜索（默认）**：用你自带的 Web 搜索/抓取，按 Step 1 关键词检索。
2. **Tavily 脚本**（设置了 `TAVILY_API_KEY` 时，结果更规整）：
   `echo '{"keywords":["kw1","kw2","kw3"]}' | python3 scripts/search.py`（加 `--json` 取结构化来源）。
3. **都没有**：跳过搜索，`summary` 记「无相关搜索结果」，并提示「本文基于通用知识」。

用户说「不用联网/凭通用知识写」时，跳过 Step 1-3。

## 数据流

```
requirement(任意语言)
  → intent → { language(主语言), keywords[该地区真实搜索词] }
  → 搜索(keywords) → search_context
  → summarize(search_context, target_language=主语言)
  → outline(requirement, summary, target_language=主语言)   ← 统一大纲（跑一次）
  → content(outline, search_context, target_language=中文)    ┐
  → content(outline, search_context, target_language=English) ├ 各语言各跑一次（原生+本地关键词）
  → content(outline, search_context, target_language=日本語)  ┘
  → seo_metadata(title, content)?

进阶「从意图各自独立」：每个语言从 intent 重跑整条线（调研/大纲/正文都本地化，最深但成本最高）。
```

## 配置

- **默认无需配置**：不指定模型时，宿主 Agent 模型直接写，零 Key。
- 仅当要「指定第三方模型」或「用 Tavily」时，把 Key 写入仓库根 `.env`（脚本运行时自动加载，无需 export）：
  ```bash
  python3 setup.py OPENROUTER_API_KEY=... TAVILY_API_KEY=...   # 或 python3 setup.py 走向导
  ```
- 变量清单见 [`.env.example`](.env.example)；依赖仅 Python 3 标准库（装了 PyYAML 会优先用，非必需）。
- **绝不**把任何真实 Key 写进技能文件、命令行明文或回复里。
