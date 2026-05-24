"""Tests for Douyin scraper module."""
from datetime import datetime
from unittest import mock

import pytest
import httpx
from click.testing import CliRunner

from financy_talk.scrapers.douyin import (
    extract_video_id,
    fetch_video_info,
    save_as_transcript,
    FetchError,
    MOBILE_UA,
)
from financy_talk.cli import main


# ---------------------------------------------------------------------------
# extract_video_id
# ---------------------------------------------------------------------------

def test_extract_video_id_from_redirect():
    resp = mock.MagicMock(spec=httpx.Response)
    resp.status_code = 302
    resp.headers = {"location": "https://www.douyin.com/video/7410058646459075840"}

    with mock.patch("httpx.Client.get", return_value=resp) as mock_get:
        vid = extract_video_id("https://v.douyin.com/abc123/")

    assert vid == "7410058646459075840"
    assert mock_get.call_args.kwargs["headers"]["User-Agent"] == MOBILE_UA


def test_extract_video_id_from_iesdouyin():
    resp = mock.MagicMock(spec=httpx.Response)
    resp.status_code = 302
    resp.headers = {
        "location": "https://www.iesdouyin.com/share/video/1234567890123456789/?region=CN"
    }

    with mock.patch("httpx.Client.get", return_value=resp):
        vid = extract_video_id("https://v.douyin.com/xyz789/")

    assert vid == "1234567890123456789"


def test_extract_video_id_no_location_raises():
    resp = mock.MagicMock(spec=httpx.Response)
    resp.status_code = 302
    resp.headers = {"location": "https://www.douyin.com/"}

    with mock.patch("httpx.Client.get", return_value=resp):
        with pytest.raises(FetchError, match="视频"):
            extract_video_id("https://v.douyin.com/badlink/")


def test_extract_video_id_http_error_propagates():
    with mock.patch("httpx.Client.get", side_effect=httpx.HTTPStatusError(
        "Not Found", request=mock.MagicMock(), response=mock.MagicMock(status_code=404)
    )):
        with pytest.raises(httpx.HTTPStatusError):
            extract_video_id("https://v.douyin.com/deadlink/")


# ---------------------------------------------------------------------------
# fetch_video_info
# ---------------------------------------------------------------------------

FAKE_HTML = """<html><body>
{"aweme_id":"7410058646459075840","desc":"AI算力板块深度分析 #财经","author":{"nickname":"阿华"},"create_time":1779753600}
</body></html>"""


def test_fetch_video_info_returns_dict():
    """Extract embedded JSON from page HTML."""
    with mock.patch("financy_talk.scrapers.douyin.sync_playwright") as mock_pw:
        mock_page = mock.MagicMock()
        mock_context = mock.MagicMock()
        mock_browser = mock.MagicMock()

        mock_pw.return_value.__enter__.return_value = mock_pw.return_value
        mock_pw.return_value.chromium.launch.return_value = mock_browser
        mock_browser.new_context.return_value = mock_context
        mock_context.new_page.return_value = mock_page
        mock_page.content.return_value = FAKE_HTML

        info = fetch_video_info("7410058646459075840")

    assert info["desc"] == "AI算力板块深度分析 #财经"
    assert info["author"] == "阿华"
    assert info["create_time"] == 1779753600
    mock_page.goto.assert_called_once()
    mock_browser.close.assert_called_once()


def test_fetch_video_info_no_aweme_raises():
    """Raise FetchError when video_id not in HTML."""
    with mock.patch("financy_talk.scrapers.douyin.sync_playwright") as mock_pw:
        mock_page = mock.MagicMock()
        mock_context = mock.MagicMock()
        mock_browser = mock.MagicMock()

        mock_pw.return_value.__enter__.return_value = mock_pw.return_value
        mock_pw.return_value.chromium.launch.return_value = mock_browser
        mock_browser.new_context.return_value = mock_context
        mock_context.new_page.return_value = mock_page
        mock_page.content.return_value = "<html><body>no data</body></html>"

        with pytest.raises(FetchError, match="无法获取视频数据"):
            fetch_video_info("0000000000000")


# ---------------------------------------------------------------------------
# save_as_transcript
# ---------------------------------------------------------------------------

def test_save_as_transcript_new_file(tmp_path):
    info = {"desc": "一条分析\n深入解读市场趋势", "create_time": 1779753600}
    path = save_as_transcript(info, "testtalker", talkers_root=tmp_path)

    assert path.exists()
    content = path.read_text(encoding="utf-8")
    assert "# 2026-05-26" in content
    assert "## 一条分析" in content
    assert "深入解读市场趋势" in content


def test_save_as_transcript_appends_to_existing_file(tmp_path):
    talker_dir = tmp_path / "testtalker"
    talker_dir.mkdir(parents=True)
    existing = talker_dir / "2026-05-26.md"
    existing.write_text("# 2026-05-26\n\n## 旧标题\n旧内容\n", encoding="utf-8")

    info = {"desc": "新标题\n新内容", "create_time": 1779753600}
    path = save_as_transcript(info, "testtalker", talkers_root=tmp_path)

    content = path.read_text(encoding="utf-8")
    assert "旧标题" in content
    assert "新标题" in content


def test_save_as_transcript_empty_desc_raises(tmp_path):
    info = {"desc": "", "create_time": 1779753600}
    with pytest.raises(FetchError, match="desc is empty"):
        save_as_transcript(info, "testtalker", talkers_root=tmp_path)


def test_save_as_transcript_no_create_time_uses_today(tmp_path):
    info = {"desc": "内容", "create_time": 0}
    path = save_as_transcript(info, "testtalker", talkers_root=tmp_path)
    today = datetime.now().strftime("%Y-%m-%d")
    assert today in path.name


def test_save_as_transcript_path_traversal_rejected(tmp_path):
    info = {"desc": "内容", "create_time": 1779753600}
    with pytest.raises(ValueError, match="Invalid talker name"):
        save_as_transcript(info, "../evil", talkers_root=tmp_path)


# ---------------------------------------------------------------------------
# CLI integration
# ---------------------------------------------------------------------------

def test_fetch_cli_success():
    """End-to-end CLI smoke test with mocked network."""
    runner = CliRunner()
    with mock.patch("financy_talk.cli.extract_video_id", return_value="12345"):
        with mock.patch("financy_talk.cli.fetch_video_info", return_value={
            "desc": "test desc\ncontent here",
            "author": "test_author",
            "create_time": 1779753600,
        }):
            with mock.patch("financy_talk.cli.save_as_transcript") as mock_save:
                mock_save.return_value = mock.MagicMock()
                result = runner.invoke(main, [
                    "fetch", "https://v.douyin.com/test/", "--talker", "t1"
                ])
                assert result.exit_code == 0
                assert "12345" in result.output
                assert "test_author" in result.output


def test_fetch_cli_bad_link():
    runner = CliRunner()
    with mock.patch("financy_talk.cli.extract_video_id",
                    side_effect=FetchError("bad link")):
        result = runner.invoke(main, [
            "fetch", "https://v.douyin.com/bad/", "--talker", "t1"
        ])
        assert result.exit_code == 1
        assert "bad link" in result.output
