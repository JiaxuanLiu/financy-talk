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
        with mock.patch("financy_talk.cli.load_talker_transcripts", return_value=["fake"]):
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
    fake_transcripts = ["fake_transcript"]
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
    assert "至少需要" in result.output


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
