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
