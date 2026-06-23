# sinkey-seo-writer

一个**搜索增强的 SEO 长文写作技能**（Agent Skill）：把「意图分析（定语言/地区）→ 联网调研 → 总结 → 大纲 → 正文 → SEO 元数据」编排成一次写作。多语言**不需要翻译**——统一大纲跑一次，再为每个目标语言各原生写一篇正文（结构跨语言一致，语言与搜索词本地化），对资讯/教程/对比类多语言站的 SEO/GEO 排名最友好。遵循 [Agent Skills](https://agentskills.io) 开放标准，可在主流 AI Agent 间复用 —— 包括 [OpenClaw](https://github.com/openclaw/openclaw)、Codex、WorkBuddy、Hermes 等。

**当前版本：** [`v1.0.0`](VERSION)

> 设计要点：**默认由你的 Agent 自己的模型写作 —— 零配置、零 API Key。** 只有当你想让某一步用某个具体第三方模型（如大纲用 gemini、正文用 deepseek），或启用 Tavily 联网搜索时，才需要配置对应 Key。

---

## 安装

把下面这句直接发给你的 Agent：

```
Install skills from https://github.com/sinkey100/Sinkey-SEO-Writer
```

> Agent 会把技能文件夹拷进它的技能目录（仓库根目录即技能根，含 `SKILL.md`）。

### 手动安装

```bash
git clone https://github.com/sinkey100/Sinkey-SEO-Writer.git
```

把仓库目录放进你的 Agent 技能加载路径（如 `~/.claude/skills/`）。**默认即可用，无需任何 Key。**

---

## 用法

加载后用自然语言即可，三种模式：

- **一条龙**：*"写一篇关于 AI 在医疗领域应用的 SEO 文章"* —— 用你写的语言所在地区从头做
- **指定地区**：*"写一篇面向美国市场的…"* / *"for the Japanese market"* / *"来个日语版"* —— 从意图步就切到该地区重做
- **单步 / 重做**：*"只生成大纲"* / *"只写正文"* / *"大纲第 3 点改…，从大纲重新来，后面接着写正文"*

指定模型（可选）：*"大纲用 gemini-3.1-pro，正文用 opus"* —— 此时该步会经 OpenRouter 用对应模型，需先配置 `OPENROUTER_API_KEY`。多语言文章可按市场价值分级用模型（核心市场上 opus，长尾语言用便宜模型）。

也可直接命令行单步运行：

```bash
# 默认路径不需要脚本，由 Agent 模型写。以下是「指定模型」时脚本的用法：
echo '{"requirement":"AI在医疗领域的应用"}' | python3 scripts/run_step.py --step intent --model deepseek/deepseek-v4-flash
echo '{"keywords":["AI in healthcare"]}'    | python3 scripts/search.py        # 需 TAVILY_API_KEY
```

---

## 配置（仅在需要指定第三方模型 / Tavily 时）

```bash
# 非交互（适合 AI Agent）：
python3 setup.py OPENROUTER_API_KEY=sk-or-xxx TAVILY_API_KEY=tvly-xxx
# 或交互式向导：
python3 setup.py
```

Key 写入仓库根 `.env`（已 gitignore），脚本运行时**自动加载，无需 export**。变量清单见 [`.env.example`](.env.example)，模型→provider→变量映射见 [`scripts/models.yaml`](scripts/models.yaml)。

---

## 更新

版本记录在 [`VERSION`](VERSION)，每次改动该文件，CI（`.github/workflows/release.yml`）自动发一个 GitHub Release。更新只需在仓库目录 `git pull`（`.env` 被忽略，不受影响）。

检查最新版：

```bash
curl -s https://raw.githubusercontent.com/sinkey100/Sinkey-SEO-Writer/main/VERSION
```

---

## 目录结构

```
sinkey-seo-writer/
├── SKILL.md            # 技能定义：name/description + 编排与模型约定
├── WORKFLOW.md         # 端到端执行细节（含 resume-from-step）
├── setup.py            # 把 API Key 写入 .env 的助手
├── .env.example        # 环境变量模板
├── VERSION
├── prompts/            # 5 段 Prompt（意图[定语言/地区]/总结/大纲/正文/SEO元数据，全程该地区语言）
└── scripts/
    ├── _env.py         # .env 自动加载
    ├── _client.py      # 多供应商 LLM 流式客户端（标准库，Key 从 env）
    ├── run_step.py     # 单步执行器 --step --model
    ├── search.py       # Tavily 多关键词搜索（可选）
    └── models.yaml     # 模型目录（无任何密钥）
```

---

## 要求

- Python 3.9+（脚本仅用标准库；装了 `PyYAML` 会优先用，非必需）
- 默认无需任何 API Key；指定第三方模型 / Tavily 时才需对应 Key

## 安全

仓库不含任何密钥；`.env` 被 gitignore。绝不要硬编码或提交 Key。
