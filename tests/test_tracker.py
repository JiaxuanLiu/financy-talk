"""Tests for tracker module (sec_uid, fetch_user_posts, dedup, README parsing)."""
import json
from unittest import mock

import pytest
import httpx

from financy_talk.scrapers.douyin import (
    extract_sec_uid,
    fetch_user_posts,
    load_extracted_ids,
    save_extracted_ids,
    parse_readme_for_profile_url,
    FetchError,
    MOBILE_UA,
)


# ---------------------------------------------------------------------------
# extract_sec_uid
# ---------------------------------------------------------------------------

def test_extract_sec_uid_from_redirect():
    resp = mock.MagicMock(spec=httpx.Response)
    resp.status_code = 302
    resp.headers = {
        "location": "https://www.douyin.com/user/MS4wLjABAAAA1XNcR5WaZ5Jrj5sjYHxCWyRIsLTe2Adj36doCCynSKw"
    }
    with mock.patch("httpx.Client.get", return_value=resp) as mock_get:
        uid = extract_sec_uid("https://v.douyin.com/abc123/")
    assert uid == "MS4wLjABAAAA1XNcR5WaZ5Jrj5sjYHxCWyRIsLTe2Adj36doCCynSKw"
    assert mock_get.call_args.kwargs["headers"]["User-Agent"] == MOBILE_UA


def test_extract_sec_uid_from_iesdouyin():
    resp = mock.MagicMock(spec=httpx.Response)
    resp.status_code = 302
    resp.headers = {
        "location": "https://www.iesdouyin.com/share/user/MS4wLjABAAAAabc?from_ssr=1"
    }
    with mock.patch("httpx.Client.get", return_value=resp):
        uid = extract_sec_uid("https://v.douyin.com/def456/")
    assert uid == "MS4wLjABAAAAabc"


def test_extract_sec_uid_no_user_raises():
    resp = mock.MagicMock(spec=httpx.Response)
    resp.status_code = 302
    resp.headers = {"location": "https://www.douyin.com/video/12345"}
    with mock.patch("httpx.Client.get", return_value=resp):
        with pytest.raises(FetchError, match="用户"):
            extract_sec_uid("https://v.douyin.com/deadlink/")


# ---------------------------------------------------------------------------
# fetch_user_posts
# ---------------------------------------------------------------------------

FAKE_POST_LIST = {
    "aweme_list": [
        {"aweme_id": "111", "desc": "post one desc"},
        {"aweme_id": "222", "desc": "post two desc"},
        {"aweme_id": "333", "desc": "post three desc"},
    ],
    "has_more": True,
    "max_cursor": 123456,
}


def test_fetch_user_posts_returns_list():
    with mock.patch("financy_talk.scrapers.douyin.sync_playwright") as mock_pw:
        mock_page = mock.MagicMock()
        mock_context = mock.MagicMock()
        mock_browser = mock.MagicMock()

        mock_pw.return_value.__enter__.return_value = mock_pw.return_value
        mock_pw.return_value.chromium.launch.return_value = mock_browser
        mock_browser.new_context.return_value = mock_context
        mock_context.new_page.return_value = mock_page

        _callbacks = {}
        def fake_on(event, cb):
            _callbacks[event] = cb
        mock_page.on = fake_on

        mock_resp = mock.MagicMock()
        mock_resp.ok = True
        mock_resp.headers = {"content-type": "application/json"}
        mock_resp.json.return_value = FAKE_POST_LIST

        def trigger(_url, **_kw):
            if "response" in _callbacks:
                _callbacks["response"](mock_resp)
        mock_page.goto = mock.MagicMock(side_effect=trigger)
        mock_page.wait_for_timeout = mock.MagicMock()

        posts = fetch_user_posts("test_uid", max_count=10)

    assert len(posts) == 3
    assert posts[0]["aweme_id"] == "111"
    assert posts[0]["desc"] == "post one desc"
    mock_browser.close.assert_called_once()


def test_fetch_user_posts_respects_max_count():
    with mock.patch("financy_talk.scrapers.douyin.sync_playwright") as mock_pw:
        mock_page = mock.MagicMock()
        mock_context = mock.MagicMock()
        mock_browser = mock.MagicMock()

        mock_pw.return_value.__enter__.return_value = mock_pw.return_value
        mock_pw.return_value.chromium.launch.return_value = mock_browser
        mock_browser.new_context.return_value = mock_context
        mock_context.new_page.return_value = mock_page

        _callbacks = {}
        def fake_on(event, cb):
            _callbacks[event] = cb
        mock_page.on = fake_on

        mock_resp = mock.MagicMock()
        mock_resp.ok = True
        mock_resp.headers = {"content-type": "application/json"}
        mock_resp.json.return_value = FAKE_POST_LIST

        def trigger(_url, **_kw):
            if "response" in _callbacks:
                _callbacks["response"](mock_resp)
        mock_page.goto = mock.MagicMock(side_effect=trigger)
        mock_page.wait_for_timeout = mock.MagicMock()

        posts = fetch_user_posts("test_uid", max_count=2)

    assert len(posts) == 2


def test_fetch_user_posts_empty_raises():
    with mock.patch("financy_talk.scrapers.douyin.sync_playwright") as mock_pw:
        mock_page = mock.MagicMock()
        mock_context = mock.MagicMock()
        mock_browser = mock.MagicMock()

        mock_pw.return_value.__enter__.return_value = mock_pw.return_value
        mock_pw.return_value.chromium.launch.return_value = mock_browser
        mock_browser.new_context.return_value = mock_context
        mock_context.new_page.return_value = mock_page
        mock_page.goto = mock.MagicMock()
        mock_page.wait_for_timeout = mock.MagicMock()

        with pytest.raises(FetchError, match="无法获取用户"):
            fetch_user_posts("bad_uid")


# ---------------------------------------------------------------------------
# Extracted-ID tracking
# ---------------------------------------------------------------------------

def test_load_extracted_ids_empty(tmp_path):
    ids = load_extracted_ids("testtalker", talkers_root=tmp_path)
    assert ids == set()


def test_save_and_load_extracted_ids(tmp_path):
    save_extracted_ids("testtalker", {"111", "222"}, talkers_root=tmp_path)
    ids = load_extracted_ids("testtalker", talkers_root=tmp_path)
    assert ids == {"111", "222"}


def test_save_extracted_ids_merges(tmp_path):
    save_extracted_ids("testtalker", {"111"}, talkers_root=tmp_path)
    save_extracted_ids("testtalker", {"222"}, talkers_root=tmp_path)
    ids = load_extracted_ids("testtalker", talkers_root=tmp_path)
    assert ids == {"111", "222"}


# ---------------------------------------------------------------------------
# README parsing
# ---------------------------------------------------------------------------

def test_parse_readme_bold_format(tmp_path):
    talker_dir = tmp_path / "testtalker"
    talker_dir.mkdir(parents=True)
    readme = talker_dir / "README.md"
    readme.write_text(
        "- **主页链接**: https://v.douyin.com/agg_B--i180/\n",
        encoding="utf-8",
    )
    url = parse_readme_for_profile_url("testtalker", talkers_root=tmp_path)
    assert url == "https://v.douyin.com/agg_B--i180/"


def test_parse_readme_markdown_link_format(tmp_path):
    talker_dir = tmp_path / "testtalker"
    talker_dir.mkdir(parents=True)
    readme = talker_dir / "README.md"
    readme.write_text(
        "- [主页链接](https://v.douyin.com/abc123/)\n",
        encoding="utf-8",
    )
    url = parse_readme_for_profile_url("testtalker", talkers_root=tmp_path)
    assert url == "https://v.douyin.com/abc123/"


def test_parse_readme_missing_file(tmp_path):
    with pytest.raises(FetchError, match="README.md 不存在"):
        parse_readme_for_profile_url("nonexistent", talkers_root=tmp_path)


def test_parse_readme_no_link(tmp_path):
    talker_dir = tmp_path / "testtalker"
    talker_dir.mkdir(parents=True)
    readme = talker_dir / "README.md"
    readme.write_text("# testtalker\njust some text\n", encoding="utf-8")

    with pytest.raises(FetchError, match="主页链接"):
        parse_readme_for_profile_url("testtalker", talkers_root=tmp_path)

