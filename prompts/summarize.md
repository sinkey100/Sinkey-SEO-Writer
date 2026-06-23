<!-- META
step: summarize
inputs:
  {{search_results}}   = 格式化后的搜索结果文本（来自 search.py 或宿主 web 搜索）
  {{target_language}}  = 目标语言/地区（由 intent 步确定）
output: 用 {{target_language}} 撰写的结构化总结，供大纲步骤使用
recommended_model: google/gemini-3.5-flash（长上下文友好、便宜）
source: backend/app/skills/summarize.py
-->

请用 {{target_language}} 阅读以下搜索结果，并总结其中的关键信息、市场观点和用户痛点，为撰写文章大纲提供参考。

搜索结果：
{{search_results}}

请提供一份结构化的总结，包含：
1. 核心观点去重
2. 竞品未覆盖的缺口
3. 用户痛点挖掘
4. 关键数据/事实引用

请用 {{target_language}} 回复。
