# Paul Graham 文集 · 中文翻译版

Paul Graham 个人网站 (paulgraham.com) 的中文翻译版，包含 **467 篇文章**的完整翻译，采用现代中文阅读体验设计。

## 在线浏览

打开 `site/index.html` 即可浏览。

## 特性

- **467 页**完整翻译（230 篇 essays + 237 其他页面）
- **1106 个**文内交叉链接保留
- **874 个**可见脚注引用 + 873 个脚注回链
- 现代响应式设计，适配手机和桌面
- 中文排版优化：PingFang SC / Microsoft YaHei 字体栈，17px 字号，1.8 行高

## 构建流程

完整的构建方案见 [BUILD_PLAYBOOK.md](BUILD_PLAYBOOK.md)，可复用于其他英文网站的中文翻译项目。

### 快速开始

```bash
# 安装依赖
pip install -r requirements.txt

# 配置 API Key
cp .env.example .env
# 编辑 .env 填入 OpenRouter API Key

# 运行完整流水线
python3 main.py

# 或分步运行
python3 main.py index      # 发现所有页面
python3 main.py scrape     # 爬取和解析
python3 main.py translate  # 翻译 (256 并发)
python3 main.py build      # 生成静态站
python3 main.py validate   # 验证
```

### 四阶段流水线

```
articles.html + homepage → [Index Builder] → data/index.json
                                    ↓
      paulgraham.com → [Scraper] → data/raw/ → data/parsed/
                                                    ↓
            OpenRouter API → [Translator] → data/translated/
                                                    ↓
                            [Generator] → site/ (static site)
```

## 翻译模型

- API: [OpenRouter](https://openrouter.ai)
- 模型: x-ai/grok-4.20-beta (2M context, $2/M input, $6/M output)
- 翻译风格: 自然流畅的中文，允许适度改写

## 项目结构

```
├── site/              # 生成的静态网站 (可直接浏览)
├── src/               # 源代码
├── templates/         # Jinja2 模板
├── main.py            # 入口
├── BUILD_PLAYBOOK.md  # 完整构建方案 (可复用)
└── requirements.txt
```

## 仅供个人学习

本站内容由 AI 翻译，仅供个人学习参考。原文版权归 Paul Graham 所有。
