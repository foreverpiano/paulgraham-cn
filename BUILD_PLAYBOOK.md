---
name: Website scrape-translate-generate playbook
description: Complete playbook for scraping an English website, translating to Chinese via LLM API, and generating a beautified static site. Derived from paulgraham.com project (18 rounds, 467 pages).
type: reference
originSessionId: 12b03854-29ca-4b8c-bea6-6932f03d4751
---
# 全站爬取→翻译→美化静态站 Playbook

## 项目概览

从英文网站生成中文美化静态站的完整流水线。适用于个人博客、文集类网站。

**实际案例**: paulgraham.com → 467页中文站，耗时约3小时API时间，翻译成本约$8-15。

## 架构：四阶段流水线

```
[Index Builder] → data/index.json
       ↓
[Scraper] → data/raw/*.html → data/parsed/*.json
       ↓
[Translator] → data/translated/*.json (async, 256并发)
       ↓
[Generator] → dist/ (static site)
```

### 关键设计决策

1. **每篇文章一次API调用**（不是逐段翻译）
   - 用 `<<<PARA_N>>>` 标记分段，整篇发送
   - 467篇 × 1次 = 467次API调用，256并发约2分钟完成
   - 逐段方案需要~10000次调用

2. **结构化占位符保留内链和脚注位置**
   - 爬取时在DOM中将 `<a href="slug.html">text</a>` 替换为 `{{LINK:slug:text}}`
   - 将 `<a href="#f1n">` 替换为 `{{FNREF:1}}`
   - 翻译后在生成阶段还原为HTML
   - **不要用文本匹配恢复链接**（会产生大量误匹配）

3. **复合缓存键**
   - `hash(source_text + model_id + prompt_version + style_config + schema_version)`
   - 任何配置变更自动使缓存失效

4. **两阶段爬取**
   - Phase 1: 解析所有页面到内存
   - Phase 2: 基于内存中的结果推导跨页关系（如 say→saynotes）
   - Phase 3: 统一写盘
   - **不要在推导阶段读取磁盘上的旧文件**

## 技术坑与解决方案

### 1. 非标准HTML解析（最大坑）
- **问题**: 老式网站用 `<font>` + `<br>` 而非 `<p>` 标签
- **解决**: 找最大的 `<font>`/`<td>` 节点 → 改为用完整 `<body>` 内容
- **教训**: "最大节点"启发式会漏掉兄弟节点中的脚注引用

### 2. 导航/宣传元素污染正文
- **问题**: YC侧边栏用 `<font color=#ff9922>`，脚注引用用 `<font color=#999999/#dddddd>`
- **解决**: 按颜色剥离宣传元素，但**跳过包含 `<a href="#fNn">` 的元素**
- **教训**: 绝不能无差别删除某种颜色的元素

### 3. 脚注格式多样性
- 格式A: `<a name="fNn">` 锚点式（PG主力格式）
- 格式B: `[N]` 纯文本 + Notes区块
- 格式C: 无脚注的文献引用 `[N]`（如 knuth.html）
- 格式D: 跨页Notes（say → saynotes.html）
- **解决**: 先提取脚注，再用footnote_ids确认哪些 `[N]` 是真脚注

### 4. Notes区块检测
- `<b>Notes</b>`, `<b>Note</b>`, `<b>Notes:</b>` 都有
- **解决**: 统一 `NOTES_HEADING_PATTERNS` 列表，大小写不敏感

### 5. 翻译模型会丢占位符
- **问题**: LLM翻译时~10%概率删除 `{{LINK:...}}` 或 `{{FNREF:N}}`
- **解决**: 译后修复——从源文本恢复丢失的占位符，删除多余的
- **教训**: 不要指望LLM 100%保留特殊标记

### 6. API Key安全
- **问题**: 用户草稿中可能包含API Key
- **解决**: 草稿文件加入 `.gitignore`，Key只存 `.env`

### 7. SOCKS代理
- **问题**: 系统有SOCKS代理时 httpx 报错
- **解决**: `pip install httpx[socks]`

## 文件结构模板

```
project/
├── main.py              # 入口: python3 main.py [index|scrape|translate|build|validate]
├── requirements.txt     # httpx[socks], beautifulsoup4, lxml, python-dotenv, jinja2
├── .env                 # API Key (gitignored)
├── .env.example
├── .gitignore
├── src/
│   ├── config.py        # 路径、API配置
│   ├── index_builder.py # BFS页面发现 + 404排除日志
│   ├── scraper.py       # 两阶段解析 + 占位符注入
│   ├── api_client.py    # OpenRouter客户端 (retry, rate limit)
│   ├── translator.py    # async 256并发 + 译后占位符修复
│   ├── cache.py         # 复合键缓存
│   ├── generator.py     # 占位符→HTML + 条件脚注回链
│   ├── validator.py     # 4层校验 + 渲染质量检查
│   └── human_review.py  # 预检worksheet生成器
├── templates/
│   ├── base.html        # 全部使用相对路径
│   ├── index.html
│   └── article.html     # 条件脚注回链
├── data/                # gitignored, 全部可重生成
│   ├── index.json
│   ├── exclusion_log.json
│   ├── raw/
│   ├── parsed/
│   ├── translated/
│   └── cache/
└── dist/                # 生成的静态站
```

## 翻译Prompt模板

```
你是一位专业的中英文翻译专家。你的任务是将用户发送的英文文本翻译成自然流畅的中文。

规则：
- 直接输出翻译结果，不要添加前缀、解释或标注
- 使用自然流畅的中文表达，允许适度改写
- 保持原文的语气和风格
- 专有名词首次出现时保留英文
- 保留所有 {{FNREF:N}} 和 {{LINK:slug:text}} 占位符
- 输入格式：<<<PARA_N>>> 标记开头，保留这些标记
- 只输出中文翻译
```

## 验证清单

- [ ] `python3 main.py validate` 退出码 = 0
- [ ] 0 断链
- [ ] 0 原始占位符泄漏
- [ ] data/exclusion_log.json 记录所有404
- [ ] 翻译缓存键包含model+prompt版本
- [ ] API Key不在git tracked文件中
- [ ] 响应式设计 (320px~1024px+)
- [ ] 人工浏览确认翻译质量

## 性能数据参考

| 指标 | 值 |
|------|-----|
| 页面数 | 467 |
| 段落数 | ~10000 |
| 翻译API调用 | 467次 (批量) |
| 翻译并发 | 256 |
| 翻译耗时 | ~2分钟 |
| 翻译成本 | ~$8-15 (grok-4.20-beta) |
| 文内交叉链接 | 1106 |
| 可见脚注引用 | 874 |
| 脚注回链 | 873 |
