# Financy Talk Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a CLI tool that analyzes financial talker transcripts via OpenAI API, generating trend reports and market assessments.

**Architecture:** Click-based CLI dispatches to data loader (Markdown parsing), AI module (OpenAI prompt/call), and reporter (terminal + file output). Each talker is a folder under `data/talkers/` with date-named `.md` files.

**Tech Stack:** Python 3.10+, click, openai, python-dotenv, pytest

---

## File Map

| File | Responsibility |
|------|---------------|
| `financy_talk/__init__.py` | Package marker, version |
| `financy_talk/config.py` | API key loading, base paths |
| `financy_talk/data/loader.py` | Parse markdown transcripts into structured data |
| `financy_talk/ai/analyzer.py` | Single-talker analysis prompt + OpenAI call |
| `financy_talk/ai/aggregator.py` | Multi-talker comparison prompt + OpenAI call |
| `financy_talk/output/reporter.py` | Terminal output + save to file |
| `financy_talk/cli.py` | Click commands: analyze, compare, list |
| `tests/test_loader.py` | Loader unit tests |
| `tests/test_analyzer.py` | Analyzer tests with mocked OpenAI |
| `tests/test_aggregator.py` | Aggregator tests with mocked OpenAI |
| `tests/test_reporter.py` | Reporter unit tests |
| `tests/test_cli.py` | CLI integration tests |
| `pyproject.toml` | Package config, entry point |
| `requirements.txt` | Dependencies |
| `data/talkers/talker1/2026-05-24.md` | Sample talker data |

---

### Task 1: Project Scaffolding

**Files:**
- Create: `pyproject.toml`
- Create: `requirements.txt`
- Create: `financy_talk/__init__.py`

- [ ] **Step 1: Write pyproject.toml**

```toml
[build-system]
requires = ["setuptools>=68.0"]
build-backend = "setuptools.backends._legacy:_Backend"

[project]
name = "financy-talk"
version = "0.1.0"
description = "AI-powered financial talker transcript analysis"
requires-python = ">=3.10"
dependencies = [
    "click>=8.0",
    "openai>=1.0",
    "python-dotenv>=1.0",
]

[project.scripts]
financy-talk = "financy_talk.cli:main"

[tool.setuptools.packages.find]
include = ["financy_talk*"]
```

- [ ] **Step 2: Write requirements.txt**

```
click>=8.0
openai>=1.0
python-dotenv>=1.0
pytest>=7.0
```

- [ ] **Step 3: Write financy_talk/__init__.py**

```python
__version__ = "0.1.0"
```

- [ ] **Step 4: Create remaining init files**

Run:
```bash
mkdir -p "F:\Python Code\Financy Talk\financy_talk\data"
mkdir -p "F:\Python Code\Financy Talk\financy_talk\ai"
mkdir -p "F:\Python Code\Financy Talk\financy_talk\output"
mkdir -p "F:\Python Code\Financy Talk\data\talkers\talker1"
mkdir -p "F:\Python Code\Financy Talk\tests"
mkdir -p "F:\Python Code\Financy Talk\output"
```

- [ ] **Step 5: Create empty __init__.py files**

Write empty files:
- `financy_talk/data/__init__.py`
- `financy_talk/ai/__init__.py`
- `financy_talk/output/__init__.py`
- `tests/__init__.py`

Run:
```bash
touch "F:\Python Code\Financy Talk\financy_talk\data\__init__.py"
touch "F:\Python Code\Financy Talk\financy_talk\ai\__init__.py"
touch "F:\Python Code\Financy Talk\financy_talk\output\__init__.py"
touch "F:\Python Code\Financy Talk\tests\__init__.py"
```

- [ ] **Step 6: Install in dev mode and verify**

Run:
```bash
cd "F:\Python Code\Financy Talk" && pip install -e .
```

Expected: Installed successfully.

- [ ] **Step 7: Commit**

```bash
cd "F:\Python Code\Financy Talk" && git add -A && git commit -m "feat: scaffold project structure"
```

---

### Task 2: Config Module

**Files:**
- Create: `financy_talk/config.py`
- Create: `tests/test_config.py`

- [ ] **Step 1: Write failing test**

```python
"""Tests for config module."""
import os
from unittest import mock
from financy_talk.config import get_api_key, DATA_DIR, OUTPUT_DIR


def test_get_api_key_from_env():
    with mock.patch.dict(os.environ, {"OPENAI_API_KEY": "sk-test123"}):
        assert get_api_key() == "sk-test123"


def test_get_api_key_from_dotenv(tmp_path):
    dotenv_file = tmp_path / ".env"
    dotenv_file.write_text("OPENAI_API_KEY=sk-dotenv456")
    with mock.patch.dict(os.environ, {}, clear=True):
        with mock.patch("financy_talk.config.PROJECT_ROOT", tmp_path):
            result = get_api_key()
    assert result == "sk-dotenv456"


def test_get_api_key_missing(tmp_path):
    with mock.patch.dict(os.environ, {}, clear=True):
        with mock.patch("financy_talk.config.PROJECT_ROOT", tmp_path):
            try:
                get_api_key()
                assert False, "Should have raised"
            except SystemExit:
                pass


def test_data_dir():
    assert DATA_DIR.name == "data"


def test_output_dir():
    assert OUTPUT_DIR.name == "output"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd "F:\Python Code\Financy Talk" && python -m pytest tests/test_config.py -v`
Expected: FAIL — module not found

- [ ] **Step 3: Write config.py implementation**

```python
"""Configuration: API key loading and base paths."""
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parent.parent

load_dotenv(PROJECT_ROOT / ".env")

DATA_DIR = PROJECT_ROOT / "data" / "talkers"
OUTPUT_DIR = PROJECT_ROOT / "output"


def get_api_key() -> str:
    key = os.getenv("OPENAI_API_KEY")
    if not key:
        print("Error: OPENAI_API_KEY not set. Set it via environment or .env file.", file=sys.stderr)
        sys.exit(1)
    return key
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd "F:\Python Code\Financy Talk" && python -m pytest tests/test_config.py -v`
Expected: PASS (5 tests)

- [ ] **Step 5: Commit**

```bash
cd "F:\Python Code\Financy Talk" && git add financy_talk/config.py tests/test_config.py && git commit -m "feat: add config module with API key loading"
```

---

### Task 3: Data Loader

**Files:**
- Create: `financy_talk/data/loader.py`
- Create: `tests/test_loader.py`

- [ ] **Step 1: Create sample markdown fixture for tests**

In `tests/test_loader.py`:

```python
"""Tests for data loader."""
import tempfile
from pathlib import Path
from financy_talk.data.loader import load_talker_transcripts, list_talkers, TalkerTranscript, TranscriptEntry


def make_talker_dir(name: str, files: dict[str, str]) -> Path:
    """Helper: create a temp talker directory with given markdown files."""
    base = Path(tempfile.mkdtemp()) / name
    base.mkdir(parents=True)
    for filename, content in files.items():
        (base / filename).write_text(content, encoding="utf-8")
    return base


SINGLE_FILE = """\
# 2026-05-20

## 半导体板块分析
今天半导体板块表现强劲，台积电业绩超预期。

## 新能源观点
锂电池产能过剩值得关注。
"""

MULTI_FILE_1 = """\
# 2026-05-20

## A板块
内容A1。

## B板块
内容B1。
"""

MULTI_FILE_2 = """\
# 2026-05-22

## C板块
内容C1。
"""

MALFORMED_FILE = """\
无标题内容，直接文本。
"""


def test_load_single_file():
    talker_dir = make_talker_dir("talker1", {"2026-05-20.md": SINGLE_FILE})
    # Temporarily override load_talker_transcripts to use custom path
    result = load_talker_transcripts("talker1", talkers_root=talker_dir.parent)
    assert len(result) == 1
    assert result[0].date == "2026-05-20"
    assert len(result[0].entries) == 2
    assert result[0].entries[0].title == "半导体板块分析"
    assert "台积电" in result[0].entries[0].content
    assert result[0].entries[1].title == "新能源观点"
    assert "锂电池" in result[0].entries[1].content


def test_load_multiple_files():
    talker_dir = make_talker_dir("talker1", {
        "2026-05-20.md": MULTI_FILE_1,
        "2026-05-22.md": MULTI_FILE_2,
    })
    result = load_talker_transcripts("talker1", talkers_root=talker_dir.parent)
    assert len(result) == 2
    dates = {r.date for r in result}
    assert dates == {"2026-05-20", "2026-05-22"}


def test_load_empty_directory():
    talker_dir = make_talker_dir("empty_talker", {})
    try:
        load_talker_transcripts("empty_talker", talkers_root=talker_dir.parent)
        assert False, "Should have raised"
    except FileNotFoundError:
        pass


def test_skip_non_md_files():
    talker_dir = make_talker_dir("talker1", {
        "2026-05-20.md": SINGLE_FILE,
        "notes.txt": "not markdown",
    })
    result = load_talker_transcripts("talker1", talkers_root=talker_dir.parent)
    assert len(result) == 1


def test_malformed_file():
    talker_dir = make_talker_dir("talker1", {"2026-05-20.md": MALFORMED_FILE})
    result = load_talker_transcripts("talker1", talkers_root=talker_dir.parent)
    assert len(result) == 1
    assert result[0].entries == []


def test_list_talkers():
    root = Path(tempfile.mkdtemp())
    (root / "talker_a").mkdir(parents=True)
    (root / "talker_b").mkdir(parents=True)
    (root / "not_a_talker.txt").write_text("nope")
    result = list_talkers(root)
    assert set(result) == {"talker_a", "talker_b"}
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd "F:\Python Code\Financy Talk" && python -m pytest tests/test_loader.py -v`
Expected: FAIL — module not found

- [ ] **Step 3: Write loader.py implementation**

```python
"""Load and parse talker transcript markdown files."""
import re
from dataclasses import dataclass, field
from pathlib import Path

from financy_talk.config import DATA_DIR


@dataclass
class TranscriptEntry:
    title: str
    content: str


@dataclass
class TalkerTranscript:
    date: str
    entries: list[TranscriptEntry] = field(default_factory=list)


def load_talker_transcripts(name: str, talkers_root: Path | None = None) -> list[TalkerTranscript]:
    root = talkers_root or DATA_DIR
    talker_dir = root / name
    if not talker_dir.is_dir():
        raise FileNotFoundError(f"Talker '{name}' not found at {talker_dir}")

    transcripts: list[TalkerTranscript] = []
    for md_file in sorted(talker_dir.glob("*.md")):
        transcript = _parse_markdown(md_file.read_text(encoding="utf-8"))
        if transcript:
            transcripts.append(transcript)
    return transcripts


def list_talkers(talkers_root: Path | None = None) -> list[str]:
    root = talkers_root or DATA_DIR
    if not root.is_dir():
        return []
    return sorted(
        d.name for d in root.iterdir()
        if d.is_dir()
    )


def _parse_markdown(text: str) -> TalkerTranscript | None:
    """Parse markdown: # Date, ## Title, then content."""
    lines = text.strip().split("\n")
    date: str | None = None
    entries: list[TranscriptEntry] = []
    current_title: str | None = None
    current_lines: list[str] = []

    for line in lines:
        if line.startswith("# ") and not line.startswith("## "):
            if date is None:
                date = line[2:].strip()
            continue
        if line.startswith("## "):
            if current_title is not None:
                entries.append(TranscriptEntry(
                    title=current_title,
                    content="\n".join(current_lines).strip(),
                ))
            current_title = line[3:].strip()
            current_lines = []
            continue
        if current_title is not None:
            current_lines.append(line)

    if current_title is not None:
        entries.append(TranscriptEntry(
            title=current_title,
            content="\n".join(current_lines).strip(),
        ))

    if date is None:
        return None
    return TalkerTranscript(date=date, entries=entries)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd "F:\Python Code\Financy Talk" && python -m pytest tests/test_loader.py -v`
Expected: PASS (6 tests)

- [ ] **Step 5: Commit**

```bash
cd "F:\Python Code\Financy Talk" && git add financy_talk/data/loader.py tests/test_loader.py && git commit -m "feat: add markdown transcript loader"
```

---

### Task 4: Reporter Module

**Files:**
- Create: `financy_talk/output/reporter.py`
- Create: `tests/test_reporter.py`

- [ ] **Step 1: Write failing test**

```python
"""Tests for reporter module."""
import tempfile
from pathlib import Path
from financy_talk.output.reporter import format_report, save_report


def test_format_report():
    content = "## Analysis\n\n这是一份分析报告。"
    result = format_report(content, talker_name="talker1", date="2026-05-24")
    assert "talker1" in result
    assert "2026-05-24" in result
    assert "## Analysis" in result


def test_save_report():
    report = "报告内容"
    output_dir = Path(tempfile.mkdtemp())
    path = save_report(report, talker_name="talker1", date="2026-05-24", output_dir=output_dir)
    assert path.exists()
    assert path.read_text(encoding="utf-8") == report


def test_save_report_creates_subdirs():
    report = "对比报告"
    output_dir = Path(tempfile.mkdtemp())
    path = save_report(report, talker_name="comparison", date="2026-05-24", output_dir=output_dir)
    assert path.exists()
    assert path.parent.name in ("comparison", "talker1")
    assert path.read_text(encoding="utf-8") == report
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd "F:\Python Code\Financy Talk" && python -m pytest tests/test_reporter.py -v`
Expected: FAIL — module not found

- [ ] **Step 3: Write reporter.py implementation**

```python
"""Format and save analysis reports."""
from pathlib import Path

from financy_talk.config import OUTPUT_DIR


def format_report(content: str, talker_name: str, date: str) -> str:
    header = f"# Financy Talk — {talker_name} 分析报告\n\n**日期:** {date}\n\n---\n\n"
    return header + content


def save_report(content: str, *, talker_name: str, date: str, output_dir: Path | None = None) -> Path:
    base = output_dir or OUTPUT_DIR
    target_dir = base / talker_name
    target_dir.mkdir(parents=True, exist_ok=True)
    filename = f"{date}_report.md"
    path = target_dir / filename
    path.write_text(content, encoding="utf-8")
    return path
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd "F:\Python Code\Financy Talk" && python -m pytest tests/test_reporter.py -v`
Expected: PASS (3 tests)

- [ ] **Step 5: Commit**

```bash
cd "F:\Python Code\Financy Talk" && git add financy_talk/output/reporter.py tests/test_reporter.py && git commit -m "feat: add reporter module for formatted output"
```

---

### Task 5: AI Analyzer (Single Talker)

**Files:**
- Create: `financy_talk/ai/analyzer.py`
- Create: `tests/test_analyzer.py`

- [ ] **Step 1: Write failing test**

```python
"""Tests for AI analyzer."""
from unittest import mock
from financy_talk.ai.analyzer import analyze_talker
from financy_talk.data.loader import TalkerTranscript, TranscriptEntry


SAMPLE_TRANSCRIPTS = [
    TalkerTranscript(
        date="2026-05-20",
        entries=[
            TranscriptEntry(title="半导体", content="台积电业绩超预期，需求旺盛。"),
            TranscriptEntry(title="新能源", content="锂电池产能过剩，价格战加剧。"),
        ],
    ),
    TalkerTranscript(
        date="2026-05-24",
        entries=[
            TranscriptEntry(title="AI算力", content="英伟达新芯片发布，算力成本下降。"),
        ],
    ),
]

FAKE_RESPONSE = "本次分析：半导体持续看好，新能源短期承压，AI算力长期利好。"


def test_analyze_talker_returns_string():
    mock_client = mock.MagicMock()
    mock_response = mock.MagicMock()
    mock_response.choices = [
        mock.MagicMock(message=mock.MagicMock(content=FAKE_RESPONSE))
    ]
    mock_client.chat.completions.create.return_value = mock_response

    result = analyze_talker("talker1", SAMPLE_TRANSCRIPTS, client=mock_client)
    assert result == FAKE_RESPONSE
    mock_client.chat.completions.create.assert_called_once()

    call_kwargs = mock_client.chat.completions.create.call_args.kwargs
    assert call_kwargs["model"] == "gpt-4o"
    messages = call_kwargs["messages"]
    assert messages[0]["role"] == "system"
    assert "财经" in messages[0]["content"]
    assert messages[1]["role"] == "user"
    assert "半导体" in messages[1]["content"]


def test_analyze_talker_empty_transcripts():
    mock_client = mock.MagicMock()
    mock_response = mock.MagicMock()
    mock_response.choices = [
        mock.MagicMock(message=mock.MagicMock(content="无数据可分析。"))
    ]
    mock_client.chat.completions.create.return_value = mock_response

    result = analyze_talker("talker1", [], client=mock_client)
    assert result == "无数据可分析。"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd "F:\Python Code\Financy Talk" && python -m pytest tests/test_analyzer.py -v`
Expected: FAIL — module not found

- [ ] **Step 3: Write analyzer.py implementation**

```python
"""Single-talker analysis via OpenAI API."""
from financy_talk.data.loader import TalkerTranscript

SYSTEM_PROMPT = """你是一位资深财经分析师。请根据以下抖音财经博主近期的视频文案，完成以下分析：

1. **核心观点总结**：提炼该博主近期表达的核心观点
2. **产业趋势分析**：根据其观点，汇总对应的产业趋势
3. **股市研判**：基于以上分析，对当前A股/港股相关板块做出研判建议

请用中文输出。格式简洁清晰。"""


def analyze_talker(
    name: str,
    transcripts: list[TalkerTranscript],
    client=None,
) -> str:
    if client is None:
        from openai import OpenAI
        from financy_talk.config import get_api_key
        client = OpenAI(api_key=get_api_key())

    user_content = _build_user_prompt(name, transcripts)

    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_content},
        ],
        temperature=0.7,
    )
    return response.choices[0].message.content


def _build_user_prompt(name: str, transcripts: list[TalkerTranscript]) -> str:
    parts = [f"博主：{name}\n"]
    for t in transcripts:
        parts.append(f"## {t.date}")
        for entry in t.entries:
            parts.append(f"### {entry.title}")
            parts.append(entry.content)
            parts.append("")
    return "\n".join(parts)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd "F:\Python Code\Financy Talk" && python -m pytest tests/test_analyzer.py -v`
Expected: PASS (2 tests)

- [ ] **Step 5: Commit**

```bash
cd "F:\Python Code\Financy Talk" && git add financy_talk/ai/analyzer.py tests/test_analyzer.py && git commit -m "feat: add single-talker AI analyzer"
```

---

### Task 6: AI Aggregator (Multi-Talker Comparison)

**Files:**
- Create: `financy_talk/ai/aggregator.py`
- Create: `tests/test_aggregator.py`

- [ ] **Step 1: Write failing test**

```python
"""Tests for AI aggregator."""
from unittest import mock
from financy_talk.ai.aggregator import aggregate_talkers
from financy_talk.data.loader import TalkerTranscript, TranscriptEntry


TALKERS_DATA = {
    "talker1": [
        TalkerTranscript(
            date="2026-05-20",
            entries=[TranscriptEntry(title="半导体", content="看好半导体，需求强劲。")],
        ),
    ],
    "talker2": [
        TalkerTranscript(
            date="2026-05-21",
            entries=[TranscriptEntry(title="新能源", content="新能源短期回调，注意风险。")],
        ),
    ],
}

FAKE_COMPARISON = "对比分析：talker1 看好半导体，talker2 看空新能源，共识方向是科技板块分化。"


def test_aggregate_talkers_returns_string():
    mock_client = mock.MagicMock()
    mock_response = mock.MagicMock()
    mock_response.choices = [
        mock.MagicMock(message=mock.MagicMock(content=FAKE_COMPARISON))
    ]
    mock_client.chat.completions.create.return_value = mock_response

    result = aggregate_talkers(TALKERS_DATA, client=mock_client)
    assert result == FAKE_COMPARISON
    mock_client.chat.completions.create.assert_called_once()

    call_kwargs = mock_client.chat.completions.create.call_args.kwargs
    messages = call_kwargs["messages"]
    assert "对比" in messages[0]["content"]
    assert "talker1" in messages[1]["content"]
    assert "talker2" in messages[1]["content"]


def test_aggregate_single_talker_falls_back():
    mock_client = mock.MagicMock()
    mock_response = mock.MagicMock()
    mock_response.choices = [
        mock.MagicMock(message=mock.MagicMock(content="只有一个博主，无法对比。"))
    ]
    mock_client.chat.completions.create.return_value = mock_response

    single_data = {"talker1": TALKERS_DATA["talker1"]}
    result = aggregate_talkers(single_data, client=mock_client)
    assert "一个" in result
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd "F:\Python Code\Financy Talk" && python -m pytest tests/test_aggregator.py -v`
Expected: FAIL — module not found

- [ ] **Step 3: Write aggregator.py implementation**

```python
"""Multi-talker comparison and aggregation via OpenAI API."""
from financy_talk.data.loader import TalkerTranscript

COMPARISON_PROMPT = """你是一位资深财经分析师。以下是多位财经博主的近期观点汇总，请完成以下分析：

1. **各博主核心观点对比**：逐位总结核心观点
2. **异同分析**：找出观点的一致性与分歧
3. **产业趋势共识**：提炼多位博主共同关注的产业方向
4. **股市综合研判**：结合多方观点，对当前A股/港股给出综合研判建议

请用中文输出。格式简洁清晰。"""


def aggregate_talkers(
    talkers_data: dict[str, list[TalkerTranscript]],
    client=None,
) -> str:
    if client is None:
        from openai import OpenAI
        from financy_talk.config import get_api_key
        client = OpenAI(api_key=get_api_key())

    user_content = _build_comparison_prompt(talkers_data)

    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": COMPARISON_PROMPT},
            {"role": "user", "content": user_content},
        ],
        temperature=0.7,
    )
    return response.choices[0].message.content


def _build_comparison_prompt(talkers_data: dict[str, list[TalkerTranscript]]) -> str:
    parts = []
    for name, transcripts in talkers_data.items():
        parts.append(f"# 博主：{name}")
        for t in transcripts:
            parts.append(f"## {t.date}")
            for entry in t.entries:
                parts.append(f"### {entry.title}")
                parts.append(entry.content)
                parts.append("")
    return "\n".join(parts)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd "F:\Python Code\Financy Talk" && python -m pytest tests/test_aggregator.py -v`
Expected: PASS (2 tests)

- [ ] **Step 5: Commit**

```bash
cd "F:\Python Code\Financy Talk" && git add financy_talk/ai/aggregator.py tests/test_aggregator.py && git commit -m "feat: add multi-talker AI aggregator"
```

---

### Task 7: CLI Entry Point

**Files:**
- Create: `financy_talk/cli.py`
- Create: `tests/test_cli.py`

- [ ] **Step 1: Write failing test**

```python
"""Tests for CLI."""
from unittest import mock
from click.testing import CliRunner
from financy_talk.cli import main


def test_list_talkers_no_data():
    runner = CliRunner()
    with mock.patch("financy_talk.cli.list_talkers", return_value=[]):
        result = runner.invoke(main, ["list"])
        assert result.exit_code == 0
        assert "没有找到" in result.output


def test_list_talkers_with_data():
    runner = CliRunner()
    with mock.patch("financy_talk.cli.list_talkers", return_value=["talker1", "talker2"]):
        result = runner.invoke(main, ["list"])
        assert result.exit_code == 0
        assert "talker1" in result.output
        assert "talker2" in result.output


def test_analyze_talker_not_found():
    runner = CliRunner()
    with mock.patch("financy_talk.cli.load_talker_transcripts", side_effect=FileNotFoundError("not found")):
        result = runner.invoke(main, ["analyze", "nonexistent"])
        assert result.exit_code != 0
        assert "not found" in result.output


def test_analyze_talker_success():
    runner = CliRunner()
    fake_transcripts = []
    fake_report = "分析报告内容"

    with mock.patch("financy_talk.cli.load_talker_transcripts", return_value=fake_transcripts):
        with mock.patch("financy_talk.cli.analyze_talker", return_value=fake_report):
            with mock.patch("financy_talk.cli.format_report", return_value="格式化报告"):
                with mock.patch("financy_talk.cli.save_report"):
                    with mock.patch("financy_talk.cli.get_api_key", return_value="sk-test"):
                        result = runner.invoke(main, ["analyze", "talker1"])
                        assert result.exit_code == 0
                        assert "格式化报告" in result.output


def test_compare_requires_two_talkers():
    runner = CliRunner()
    result = runner.invoke(main, ["compare", "talker1"])
    assert result.exit_code != 0
    assert "至少需要" in result.output or "argument" in result.output.lower()


def test_compare_success():
    runner = CliRunner()
    fake_report = "对比分析结果"

    with mock.patch("financy_talk.cli.load_talker_transcripts", return_value=[]):
        with mock.patch("financy_talk.cli.aggregate_talkers", return_value=fake_report):
            with mock.patch("financy_talk.cli.format_report", return_value="格式化对比报告"):
                with mock.patch("financy_talk.cli.save_report"):
                    with mock.patch("financy_talk.cli.get_api_key", return_value="sk-test"):
                        result = runner.invoke(main, ["compare", "talker1", "talker2"])
                        assert result.exit_code == 0
                        assert "格式化对比报告" in result.output
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd "F:\Python Code\Financy Talk" && python -m pytest tests/test_cli.py -v`
Expected: FAIL — module not found

- [ ] **Step 3: Write cli.py implementation**

```python
"""CLI entry point for financy-talk."""
import sys
from datetime import date

import click

from financy_talk.config import get_api_key
from financy_talk.data.loader import load_talker_transcripts, list_talkers
from financy_talk.ai.analyzer import analyze_talker
from financy_talk.ai.aggregator import aggregate_talkers
from financy_talk.output.reporter import format_report, save_report


@click.group()
def main():
    """Financy Talk — AI-powered financial talker transcript analysis."""


@main.command()
@click.argument("name")
def analyze(name: str):
    """分析单个 talker 的文案，生成趋势研判报告。"""
    try:
        transcripts = load_talker_transcripts(name)
    except FileNotFoundError as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)

    if not transcripts:
        click.echo(f"Talker '{name}' has no transcript files.")
        sys.exit(1)

    click.echo(f"正在分析 {name} ({len(transcripts)} 篇文案)...")
    _ = get_api_key()
    result = analyze_talker(name, transcripts)
    today = date.today().isoformat()
    formatted = format_report(result, talker_name=name, date=today)
    click.echo(formatted)
    path = save_report(formatted, talker_name=name, date=today)
    click.echo(f"\n报告已保存到：{path}")


@main.command()
@click.argument("names", nargs=-1, required=True)
def compare(names: tuple[str, ...]):
    """对比多个 talker 的观点，生成综合研判报告。"""
    if len(names) < 2:
        click.echo("Error: 至少需要两个 talker 进行对比。", err=True)
        sys.exit(1)

    talkers_data: dict[str, list] = {}
    for name in names:
        try:
            talkers_data[name] = load_talker_transcripts(name)
        except FileNotFoundError as e:
            click.echo(f"Error: {e}", err=True)
            sys.exit(1)

    total = sum(len(t) for t in talkers_data.values())
    click.echo(f"正在对比 {', '.join(names)} ({total} 篇文案)...")
    _ = get_api_key()
    result = aggregate_talkers(talkers_data)
    today = date.today().isoformat()
    formatted = format_report(result, talker_name="comparison", date=today)
    click.echo(formatted)
    path = save_report(formatted, talker_name="comparison", date=today)
    click.echo(f"\n报告已保存到：{path}")


@main.command("list")
def list_command():
    """列出所有已添加的 talker。"""
    talkers = list_talkers()
    if not talkers:
        click.echo("没有找到任何 talker。请在 data/talkers/ 下创建文件夹。")
        return
    click.echo("已添加的 Talker：")
    for t in talkers:
        try:
            transcripts = load_talker_transcripts(t)
            count = len(transcripts)
            click.echo(f"  - {t} ({count} 篇文案)")
        except FileNotFoundError:
            click.echo(f"  - {t} (0 篇文案)")
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd "F:\Python Code\Financy Talk" && python -m pytest tests/test_cli.py -v`
Expected: PASS (6 tests)

- [ ] **Step 5: Commit**

```bash
cd "F:\Python Code\Financy Talk" && git add financy_talk/cli.py tests/test_cli.py && git commit -m "feat: add CLI with analyze, compare, list commands"
```

---

### Task 8: Sample Data & End-to-End Verification

**Files:**
- Create: `data/talkers/talker1/2026-05-24.md`

- [ ] **Step 1: Create sample talker data**

Write `data/talkers/talker1/2026-05-24.md`:

```markdown
# 2026-05-24

## AI算力板块观点
英伟达最新一季度财报超预期，算力需求依然强劲。国内AI芯片替代加速，关注寒武纪、海光信息。

## 新能源光伏讨论
光伏组件价格触底反弹，欧洲需求回暖。隆基绿能、通威股份值得重点关注。
```

- [ ] **Step 2: Verify CLI list command works**

Run: `cd "F:\Python Code\Financy Talk" && financy-talk list`
Expected: Shows "talker1 (1 篇文案)"

- [ ] **Step 3: Verify analyze works (dry run without API key)**

Run: `cd "F:\Python Code\Financy Talk" && financy-talk analyze talker1`
Expected: If no API key set, gives clear error message. If API key set, runs analysis.

- [ ] **Step 4: Run full test suite**

Run: `cd "F:\Python Code\Financy Talk" && python -m pytest tests/ -v`
Expected: All tests pass.

- [ ] **Step 5: Commit**

```bash
cd "F:\Python Code\Financy Talk" && git add data/talkers/talker1/2026-05-24.md && git commit -m "feat: add sample talker data"
```

---

### Task 9: Initialize Git Repository

- [ ] **Step 1: Initialize git repo**

```bash
cd "F:\Python Code\Financy Talk" && git init
```

- [ ] **Step 2: Create .gitignore**

Write `.gitignore`:

```
__pycache__/
*.pyc
.venv/
venv/
.env
*.egg-info/
dist/
build/
output/reports/
```

- [ ] **Step 3: Commit .gitignore**

```bash
cd "F:\Python Code\Financy Talk" && git add .gitignore && git commit -m "chore: add .gitignore"
```
