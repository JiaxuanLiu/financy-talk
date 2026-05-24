# Financy Talk — Design Spec

## Overview

财经类 AI 分析工具。将不同抖音 talker 的视频文案汇总到 Markdown 文件，通过 OpenAI API 分析各 talker 的产业观点，生成趋势研判和股市分析报告。

## Architecture

```
CLI (click)
    │
    ├── analyze <talker>         # 单个 talker 分析
    ├── compare <talkers...>     # 多 talker 对比汇总
    ├── list                     # 列出所有 talker
    │
    ▼
Data Layer (loader.py)
    扫描 data/talkers/<name>/*.md → 结构化 dict
    │
    ▼
AI Layer (analyzer.py / aggregator.py)
    拼接 prompt → 调用 OpenAI API → 返回分析结果
    │
    ▼
Reporter (reporter.py)
    格式化输出 → 终端 + 保存 output/
```

## Directory Structure

```
financy-talk/                    # 项目根目录
├── financy_talk/                # Python 包
│   ├── __init__.py
│   ├── cli.py                   # CLI 入口 (click)
│   ├── config.py                # 配置 (API key, 路径等)
│   ├── data/
│   │   ├── __init__.py
│   │   └── loader.py            # Markdown 读取解析
│   ├── ai/
│   │   ├── __init__.py
│   │   ├── analyzer.py          # 单 talker 分析
│   │   └── aggregator.py        # 多 talker 对比汇总
│   └── output/
│       ├── __init__.py
│       └── reporter.py          # 输出格式化
├── data/talkers/                # Talker 数据
│   └── talker1/
│       └── 2026-05-24.md
├── output/                      # 分析报告输出
│   └── talker1/
│       └── 2026-05-24_report.md
├── tests/
├── pyproject.toml
└── requirements.txt
```

## Data Flow

### 单 Talker 分析 (`analyze`)

```
data/talkers/<name>/*.md
    → loader 读取全部 .md 文件
    → analyzer 组装 prompt (系统 prompt + 文案内容)
    → OpenAI API 调用
    → reporter 终端输出 + 保存 output/<name>/<date>_report.md
```

### 多 Talker 对比 (`compare`)

```
data/talkers/<name1>/*.md + data/talkers/<name2>/*.md ...
    → loader 同时读取多名 talker 数据
    → aggregator 组装对比 prompt
    → OpenAI API 调用
    → reporter 终端输出 + 保存 output/comparisons/<date>_comparison.md
```

## Talker Data Format

每个 talker 是个 `data/talkers/<name>/` 文件夹，内含按日期命名的 Markdown 文件：

```markdown
# 2026-05-24

## 视频标题 1
文案内容...

## 视频标题 2
文案内容...
```

## AI Prompt Design

分析 prompt 分三部分：
1. **角色设定** — 资深财经分析师
2. **任务指令** — 总结核心观点 → 提炼产业趋势 → 股市研判
3. **输入数据** — 拼接所有 Markdown 文件内容

对比 prompt 额外包含：跨 talker 观点异同分析、共识方向识别。

## Key Dependencies

- `click` — CLI 框架
- `openai` — OpenAI API SDK
- `pyyaml` — 未来配置文件解析 (可选)

## CLI Commands

```bash
# 激活虚拟环境后
financy-talk analyze talker1
financy-talk compare talker1 talker2
financy-talk list
```

## Non-Goals (本期不做)

- 定时自动运行
- Web UI
- 抖音 API 自动抓取
- meta.yaml 配置解析（需要时再加）

## Test Strategy

- `loader` — 单元测试，用 fixture 构造 Markdown 文件
- `analyzer` / `aggregator` — 集成测试，mock OpenAI 响应
- `cli` — 用 click 的 CliRunner 做端到端测试
