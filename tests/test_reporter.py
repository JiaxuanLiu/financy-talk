"""Tests for reporter module."""
from pathlib import Path
from unittest import mock

import pytest

from financy_talk.output.reporter import format_report, save_report


def test_format_report():
    content = "## Analysis\n\n这是一份分析报告。"
    result = format_report(content, talker_name="talker1", date="2026-05-24")
    assert "talker1" in result
    assert "2026-05-24" in result
    assert "## Analysis" in result


def test_save_report(tmp_path):
    report = "报告内容"
    output_dir = tmp_path / "output"
    path = save_report(report, talker_name="talker1", date="2026-05-24", output_dir=output_dir)
    assert path.exists()
    assert path.read_text(encoding="utf-8") == report


def test_save_report_creates_subdirs(tmp_path):
    report = "对比报告"
    output_dir = tmp_path / "output"
    path = save_report(report, talker_name="comparison", date="2026-05-24", output_dir=output_dir)
    assert path.exists()
    assert path.parent.name == "comparison"
    assert path.read_text(encoding="utf-8") == report


def test_save_report_uses_default_output_dir(tmp_path):
    report = "测试"
    output_dir = tmp_path / "default_output"
    output_dir.mkdir()
    with mock.patch("financy_talk.output.reporter.OUTPUT_DIR", output_dir):
        path = save_report(report, talker_name="talker1", date="2026-05-24")
        assert output_dir in path.parents
        assert path.read_text(encoding="utf-8") == report


def test_save_report_rejects_traversal(tmp_path):
    output_dir = tmp_path / "output"
    with pytest.raises(ValueError, match="Invalid talker name"):
        save_report("x", talker_name="../etc", date="2026-05-24", output_dir=output_dir)
    with pytest.raises(ValueError, match="Invalid talker name"):
        save_report("x", talker_name="foo/bar", date="2026-05-24", output_dir=output_dir)
    with pytest.raises(ValueError, match="Invalid talker name"):
        save_report("x", talker_name="foo\\bar", date="2026-05-24", output_dir=output_dir)
