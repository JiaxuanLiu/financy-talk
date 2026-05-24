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
