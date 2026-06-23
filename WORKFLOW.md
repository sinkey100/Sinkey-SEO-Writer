# WORKFLOW — SEO 长文写作流水线

本文件给出端到端的执行细节，配合 [`SKILL.md`](SKILL.md) 使用。

## 总览

```
用户需求 requirement（任意语言）
   │
   ├─ Step 1 意图分析 ──→ { language(=target_language), keywords[3]（该地区真实搜索词） }
   │        确定本文语言/地区：用户在意图里点名了地区就用它，否则按书写语言推断地区
   │
   ├─ Step 2 联网调研（可选）──→ 搜索结果（去重+格式化，自然偏该地区）
   │        优先级: 宿主 web 搜索 → Tavily 脚本(有 key) → 跳过(降级)
   │
   ├─ Step 3 总结 ──→ summary（== search_context，用 target_language）  输入: search_results + target_language
   │
   ├─ Step 4 大纲（统一大纲，跑一次）──→ outline.md（用主语言，关键词为该地区真实搜索词）  输入: requirement + summary + target_language(主语言)
   │
   ├─ Step 5 正文 ──→ article.<lang>.md   输入: outline + search_context + target_language
   │        多语言站：统一大纲跑一次，再为每个目标语言各跑一次本步（换 target_language）
   │        与大纲语言无关 —— 永远用 target_language 原生写 + 本地化关键词，结构/章节与大纲一致
   │
   └─ SEO 元数据（可选）──→ metadata.json（与正文同语言）  输入: title + article
```

> **多语言默认（推荐，适合资讯/教程/对比多语言站）：统一大纲 + 各地区原生正文。**
> 主语言跑 Step 1→4 出统一大纲，再为每个语言各跑一次 Step 5（换 target_language）。结构/章节/观点跨语言一致，语言与搜索词本地化。
>
> **进阶（某市场需完全不同调研角度/选题，如各地区竞品不同）：从意图各自独立**——每个语言从 Step 1 重跑整条线。本地化最深，但各版本叙事可能不同、成本最高。

## 三种用法的执行细节

### A. 一条龙（主语言）
1. 跑 Step 1→5（主语言，由 Step 1 确定）。
2. 每步产出**落盘**：`outline.md`、`article.md`（统一大纲 + 主语言正文）。
3. 要其它语言 → 见 B；要元数据 → 追加 SEO 元数据步。
4. 全程默认用宿主模型；用户为某步点了模型，则该步走 `run_step.py`。

### B. 多语言（统一大纲）
1. 用 A 的统一大纲（`outline.md`）。
2. 为每个目标语言各跑一次 Step 5（content），`target_language` 换成该语言，输入同一份 outline + search_context。
3. 各自落盘 `article.en.md` / `article.ja.md` / …；可按市场价值分级用模型（核心市场 opus，长尾语言便宜模型）。
4. 多产品对比若各地区竞品不同：在大纲层按地区把产品清单换一下，再跑该地区 content（可选增强）。

### C. 单步 / 从指定步骤重做并继续
- **单步**：只跑被点名的那一步，输入按下表的 JSON 键准备。
- **重做并续跑**：从步骤 N 重跑后续；改了大纲后记得重跑各语言 content（Step 5）。
- **进阶（从意图各自独立）**：换语言/换地区调研时，从 Step 1（intent）重跑整条线。

## 委托脚本时的输入/输出契约

| step | stdin JSON | 输出(stdout) |
|---|---|---|
| `intent` | `{"requirement": "..."}` | JSON：`{"language": "目标语言/地区", "keywords": ["该地区搜索词1","2","3"]}` |
| `summarize` | `{"search_results": "<格式化文本>", "target_language": "English"}` | 用该语言的结构化总结文本 |
| `outline` | `{"requirement":"...","summary":"...","target_language":"English"}` | 该语言的 Markdown 大纲（含本地关键词） |
| `content` | `{"outline":"...","search_context":"...","target_language":"English"}` | 该语言的 Markdown 正文 |
| `seo_metadata` | `{"title":"...","content":"..."}` | JSON：`{slug,title,description,keywords}` |

> `target_language`：summarize/outline 用 intent 确定的**主语言**（跑一次）；**content 按需换语言**（多语言站每语言各跑一次）。content 与大纲语言无关，永远原生用 target_language 写 + 本地化关键词。

退出码：`0` 成功；`2` 缺对应 API Key（把错误转达用户，不重试）；`3` 未知模型/步骤；`1` 其他。

## 写作要点（默认宿主模型也须遵守）
- **正文**：E-E-A-T + 费曼降维、短句、列表化、段落≤4 行、加粗重点；严禁编造参数/价格；保持第三方中立；无开场白/结束语/竞品推荐。
- **语言/地区**：summarize/outline 用主语言；content 用各 `target_language` 原生写 + 本地化关键词（不要直译大纲里的词）。结构/章节/观点与统一大纲保持一致（跨语言对应得上）。本地化日期/货币/度量与案例；品牌名保留。
- **SEO 元数据**：slug 始终英文连字符；标题≤60、描述≤160、关键词≤100，且与正文同语言。
