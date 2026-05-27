# Financy Talk

AI 驱动的财经舆情分析工具。汇总抖音财经 talker 的视频文案，通过 AI 提炼行业观点构建知识库，自动生成产业趋势研判和股市分析报告。

## 安装

```bash
pip install -e .
```

## 环境配置

设置 DeepSeek API Key（三选一，优先级从高到低）：

```bash
export DEEPSEEK_API_KEY=sk-xxxxx              # 方式一：环境变量
echo 'DEEPSEEK_API_KEY=sk-xxxxx' > .env       # 方式二：.env 文件
# 方式三：settings.yaml 的 api_key 字段（见 settings.example.yaml）
```

> DeepSeek API Key 可在 https://platform.deepseek.com/api_keys 获取。

## 数据准备

在 `data/talkers/` 下为每个博主创建文件夹，包含两个文件：

### README.md — 博主信息与信任评分

```markdown
# 博主名称

- **平台**: 抖音
- **主页链接**: https://v.douyin.com/xxxxx/
- **简介**: 机构一手调研
- **备注**: 行业研究
- **短期信任评分**：85分（满分100分）
- **中期信任评分**：95分（满分100分）
- **长期信任评分**：90分（满分100分）
```

信任评分表示该博主在不同时间尺度上的判断可靠性：
- **短期**（5 天内）：最近的市场节奏和短线观点
- **中期**（20 天内）：趋势判断和方向性预测
- **长期**（6 个月内）：产业格局和长期研判

### YYYY-MM-DD.md — 视频文案

```markdown
# 2026-05-27

## CCL涨价分析
建滔发布年内第四次涨价函，全产业链零库存，即产即销……

## CPO技术突破
台积电CSP基板技术提前量产，解决良率和成本痛点……
```

> 所有 `data/talkers/` 下的内容均被 `.gitignore` 排除（版权保护），不会上传到 Git。

## 完整工作流

```bash
# ① 文案清洗 — AI 逐篇去除口语化、提炼关键信息（haiku 模型，低成本）
financy-talk digest <name>

# ② 构建知识库 — 从清洗后的文案提取行业观点，合并到知识库
financy-talk build-kb <name>           # 增量更新（最近 5 天）
financy-talk build-kb <name> --all     # 首次初始化（全部历史文案）

# ③ 分析报告 — 结合知识库 + 信任评分 + 最新观点生成研判报告
financy-talk analyze <name>

# ④ 多博主对比 — 对比多个 talker 观点，生成综合研判
financy-talk compare <name1> <name2>
```

报告同时输出到终端并保存到 `output/<name>/YYYY-MM-DD_report.md`。

## CLI 命令参考

| 命令 | 说明 |
|---|---|
| `financy-talk list` | 列出所有 talker，显示文案数、信任评分、知识库状态 |
| `financy-talk digest <name> [--force]` | 清洗文案：AI 逐篇去除口语化、提炼关键信息点 |
| `financy-talk build-kb <name> [--all]` | 构建/更新知识库，默认处理最近 5 天 |
| `financy-talk analyze <name>` | AI 分析单个 talker，生成产业趋势研判和股市建议 |
| `financy-talk compare <n1> <n2>` | AI 对比多个 talker，生成综合研判报告 |

## 架构

```
data/talkers/<name>/*.md     ← 用户手动整理文案
        ↓ digest
data/talkers/<name>/digest/  ← AI 清洗后的精炼文本
        ↓ build-kb
data/talkers/<name>/kb.json   ← 结构化知识库（行业节点 + 论据）
        ↓ analyze
output/<name>/report.md      ← 最终分析报告
```

三层 AI 调用：
- **haiku**（digest）：逐篇清洗，低成本批量处理
- **sonnet**（analyze / build-kb）：单博主分析、知识库提取
- **opus**（compare / build-kb --all）：多博主对比、全量知识库构建

模型和参数可在 `settings.yaml` 中配置，模板见 `settings.example.yaml`。

## 项目结构

```
financy-talk/
├── financy_talk/
│   ├── cli.py                   # CLI 入口
│   ├── config.py                # 配置管理（API key、模型分级）
│   ├── data/
│   │   ├── loader.py            # 文案解析 + 信任评分 + 时间窗口
│   │   ├── digest.py            # 单篇文案 AI 清洗
│   │   ├── kb_schema.py         # 知识库数据结构
│   │   └── kb_builder.py        # 知识库构建与合并
│   ├── ai/
│   │   ├── analyzer.py          # 单 talker 分析（KB + 信任评分）
│   │   └── aggregator.py        # 多 talker 对比
│   ├── output/reporter.py       # 报告输出
│   └── scrapers/                # 抖音/豆包抓取（不再通过 CLI 暴露）
├── data/talkers/                # Talker 数据（gitignore）
│   └── TEMPLATE.md              # 文案格式模板
├── tests/                       # 测试
├── settings.example.yaml        # 配置模板
└── pyproject.toml
```

## 运行测试

```bash
python -m pytest tests/ -v
```

## 依赖

- Python 3.10+
- DeepSeek API（兼容 OpenAI SDK）
- Click、PyYAML、python-dotenv
