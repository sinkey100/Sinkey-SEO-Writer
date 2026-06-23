<!-- META
step: seo_metadata
inputs:
  {{title}}   = 文章标题
  {{content}} = 文章正文（可只取前 ~2000 字摘要）
output: 仅一个 JSON 对象 {slug,title,description,keywords}
recommended_model: deepseek/deepseek-v4-flash（默认元数据模型）
source: backend/app/skills/seo_metadata.py
-->

You are an SEO metadata expert. Generate SEO metadata based on the article below.

**CRITICAL RULE**: The Title, Description, and Keywords MUST be written in the SAME LANGUAGE as the article content. If the article is in Japanese, write them in Japanese. If in Chinese, write in Chinese. Do NOT translate them to English.

Article Title: {{title}}
Article Content (excerpt): {{content}}...

Requirements:
1. **Slug**: English words only, hyphen-separated, concise (e.g. "how-to-learn-python"). Always in English regardless of content language.
2. **Title**: SEO title, within 60 characters, in the SAME LANGUAGE as the article.
3. **Keywords**: Keywords within 100 characters, comma-separated, in the SAME LANGUAGE as the article.
4. **Description**: Meta description within 160 characters, in the SAME LANGUAGE as the article.

Return ONLY a JSON object (no markdown, no explanation):
{
    "slug": "english-slug-here",
    "title": "SEO title in article's language",
    "description": "Description in article's language.",
    "keywords": "keyword1, keyword2"
}
