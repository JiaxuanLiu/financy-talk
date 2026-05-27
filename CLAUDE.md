# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 常用命令

```bash
# 安装开发环境
pip install -e .

# 运行所有测试
python -m pytest tests/ -v

# 运行单个测试文件
python -m pytest tests/test_loader.py -v

# 运行单个测试用例
python -m pytest tests/test_loader.py::test_load_single_file -v

# CLI 命令
financy-talk list                          # 列出所有 talker（含信任评分和 KB 状态）
financy-talk analyze <name>                # 分析单个 talker（自动加载 KB 和信任评分）
financy-talk compare <name1> <name2>       # 对比多个 talker
financy-talk build-kb <name>               # 从最近5天文案更新知识库
financy-talk build-kb <name> --all         # 从全部历史文案重建知识库
```

## 架构概览

```
CLI (cli.py)
  ├── analyze  → Data Layer → AI Layer (analyzer, "sonnet") → Reporter
  ├── compare  → Data Layer → AI Layer (aggregator, "opus")  → Reporter
  ├── list     → Data Layer
  └── build-kb → KB Builder (AI 提取行业观点) → kb.json
```

### Data Layer (`data/loader.py`, `data/kb_schema.py`, `data/kb_builder.py`)

**文案解析**：解析 `data/talkers/<name>/*.md` 为 `TalkerTranscript` 结构。Talker 名称禁止包含 `..`、`/`、`\`（防路径穿越）。只加载 `.md` 文件。

**信任评分**：每个 talker 的 `README.md` 中包含三项评分：
- 短期信任评分（0-5天）
- 中期信任评分（5-20天）
- 长期信任评分（20天-6个月）

`parse_trust_scores()` 用正则提取这些评分，返回 `TrustScores` 对象。

**时间窗口**：`split_by_time_window()` 将文案按 5天/20天/180天 分为短/中/长三组，超过 180 天的丢弃。

**知识库**（`kb.json`）：每个 talker 维护一个结构化知识库，通过 AI 从近期文案中提取行业观点：

```
{
  "updated": "2026-05-27",
  "nodes": {
    "CCL/PCB": {
      "core_claim": "全球CCL进入20年最严重缺货周期",
      "confidence": "high",
      "trend": "accelerating",
      "evidence": [{"date": "2026-05-27", "point": "电子布库存告急"}]
    }
  }
}
```

- `build_kb()` 调 AI 提取最近 5 天文案中的行业节点，与现有 KB 合并（同名节点追加 evidence，更新 core_claim/trend）
- `archive_stale_evidence()` 清理超过 180 天的论据（每条节点至少保留 3 条）
- KB 文件路径：`data/talkers/<name>/kb.json`

### AI Layer (`ai/analyzer.py`, `ai/aggregator.py`)

通过 OpenAI SDK 调用 DeepSeek API。model tier 系统：
- **haiku**: 快速/轻量（默认 max_tokens=2000）
- **sonnet**: 标准分析和 KB 提取使用（默认 max_tokens=4000）
- **opus**: 深度对比，`compare` 使用（默认 max_tokens=8000）

模型和 max_tokens 可在 `settings.yaml` 中覆盖。

**Analyze 的 prompt 结构**（有 KB 时）：
1. 信任评分提示（标注该博主哪个时间尺度判断力最强）
2. 知识库积累（各行业节点的核心判断 + 趋势方向 + 关键论据）
3. 最新观点（5 天内全文，作为决策核心）

无 KB 时回退为扁平拼接所有文案。

**Aggregate 的 prompt 结构**：
每个 talker 并排展示：信任评估 + KB 摘要 + 短期全文。system prompt 指示 AI：观点冲突时优先采信对应时间尺度上信任评分更高的博主。

### Config (`config.py`)
API key 优先级：`DEEPSEEK_API_KEY` 环境变量 > `.env` 文件 > `settings.yaml` 的 `api_key` 字段。
`settings.yaml` 被 `.gitignore` 排除；`settings.example.yaml` 是模板。

### Reporter (`output/reporter.py`)
格式化报告并保存到 `output/<talker_name>/YYYY-MM-DD_report.md`。

## Talker 数据格式

每个 talker 是 `data/talkers/<name>/` 目录：
- `README.md` — 元信息和信任评分（必填，analyze 和 compare 会读取）
- `YYYY-MM-DD.md` — 按日期组织的文案，格式：`# 日期` + `## 标题` + 内容
- `kb.json` — 自动生成的知识库（build-kb 命令创建）
- `backup/` — 手动备份目录（loader 不递归读取，天然隔离）

## 关键约束

- Talker 名称禁止包含 `..`、`/`、`\`（防路径穿越）
- `data/talkers/*` 被 `.gitignore` 整体排除，仅 `TEMPLATE.md` 例外（版权保护）
- `settings.yaml` 已被 gitignore，模板是 `settings.example.yaml`
- DeepSeek API 兼容 OpenAI SDK，`base_url` 固定为 `https://api.deepseek.com`
- API 调用超时为 120 秒，analyze/compare 的 temperature 为 0.7，KB 提取为 0.3
- KB 的 `archive_stale_evidence()` 有"至少保留 3 条"的安全阀，仅在原证据数 > 3 时触发
