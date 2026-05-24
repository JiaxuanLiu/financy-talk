# Financy Talk

AI 驱动的财经舆情分析工具。汇总抖音财经 talker 的视频文案，通过 OpenAI API 自动生成产业趋势研判和股市分析报告。

## 安装

```bash
pip install -e .
```

## 环境配置

设置 OpenAI API Key（二选一）：

```bash
# 方式一：环境变量
export OPENAI_API_KEY=sk-xxxxx

# 方式二：.env 文件（放在项目根目录）
echo 'OPENAI_API_KEY=sk-xxxxx' > .env
```

## 快速开始

### 1. 添加 Talker 数据

在 `data/talkers/` 下为每个博主创建文件夹，按日期添加视频文案（Markdown 格式）：

```
data/talkers/
├── talker1/
│   ├── 2026-05-20.md
│   └── 2026-05-24.md
├── talker2/
│   └── 2026-05-24.md
```

文案文件格式：

```markdown
# 2026-05-24

## AI算力板块观点
英伟达最新一季度财报超预期，算力需求依然强劲。

## 新能源光伏讨论
光伏组件价格触底反弹，欧洲需求回暖。
```

### 2. 运行分析

```bash
# 列出所有 talker
financy-talk list

# 分析单个 talker
financy-talk analyze talker1

# 对比多个 talker
financy-talk compare talker1 talker2
```

分析报告会同时显示在终端并保存到 `output/` 目录。

## 项目结构

```
financy-talk/
├── financy_talk/
│   ├── cli.py              # CLI 入口
│   ├── config.py           # 配置管理
│   ├── data/loader.py      # 文案解析
│   ├── ai/analyzer.py      # 单 talker 分析
│   ├── ai/aggregator.py    # 多 talker 对比
│   └── output/reporter.py  # 报告输出
├── data/talkers/           # Talker 数据
├── output/                 # 分析报告
├── tests/                  # 测试
└── docs/superpowers/       # 设计文档
```

## 运行测试

```bash
python -m pytest tests/ -v
```

## 依赖

- Python 3.10+
- OpenAI API
- Click
