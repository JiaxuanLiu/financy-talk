"""Extract video text from Douyin share links."""
import re
from datetime import datetime
from pathlib import Path

import httpx
from playwright.sync_api import sync_playwright

from financy_talk.config import DATA_DIR

MOBILE_UA = (
    "Mozilla/5.0 (Linux; Android 13; SM-S9080) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/120.0.0.0 Mobile Safari/537.36"
)


class FetchError(RuntimeError):
    """Failed to fetch video info."""


def extract_video_id(share_url: str) -> str:
    """Extract numeric video_id from a v.douyin.com share link."""
    with httpx.Client(follow_redirects=False, timeout=15) as client:
        response = client.get(share_url, headers={"User-Agent": MOBILE_UA})
        # 3xx responses are legit; only raise for 4xx/5xx
        if response.status_code >= 400:
            response.raise_for_status()

    location = response.headers.get("location", "")
    match = re.search(r"/video/(\d+)", location)
    if not match:
        # Might be a user profile link or other non-video page
        if "/user/" in location:
            raise FetchError(
                "该链接是用户主页，不是单个视频。请从抖音 App 复制单个视频的分享链接。"
            )
        raise FetchError(
            f"无法从跳转链接中提取视频ID，请确认是抖音视频分享链接。跳转: {location}"
        )
    return match.group(1)


def fetch_video_info(video_id: str) -> dict:
    """Open the Douyin video page in a headless browser and extract
    embedded JSON data containing desc / author / create_time.
    """
    video_url = f"https://www.douyin.com/video/{video_id}"

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent=MOBILE_UA,
            viewport={"width": 390, "height": 844},
        )
        page = context.new_page()
        page.goto(video_url, wait_until="networkidle", timeout=30000)
        page.wait_for_timeout(3000)
        html = page.content()
        browser.close()

    # Extract inline JSON containing aweme_id (balanced braces)
    import json
    marker = f'"aweme_id":"{video_id}"'
    idx = html.find(marker)
    if idx == -1:
        raise FetchError(
            f"无法获取视频数据（可能是反爬限制），请稍后重试。video_id={video_id}"
        )

    # Find the opening brace before the marker
    brace_start = html.rfind("{", 0, idx)
    if brace_start == -1:
        raise FetchError(f"解析视频数据失败。video_id={video_id}")

    # Walk forward counting brace depth
    depth = 0
    brace_end = brace_start
    for i in range(brace_start, len(html)):
        ch = html[i]
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                brace_end = i + 1
                break

    raw = html[brace_start:brace_end]
    try:
        aweme = json.loads(raw)
    except json.JSONDecodeError:
        raise FetchError(f"解析视频数据失败。video_id={video_id}")

    return {
        "desc": aweme.get("desc", ""),
        "author": (aweme.get("author") or {}).get("nickname", ""),
        "create_time": aweme.get("create_time", 0),
    }


def save_as_transcript(
    video_info: dict,
    talker_name: str,
    talkers_root: Path | None = None,
) -> Path:
    """Write the video info as a Markdown transcript file."""
    if ".." in talker_name or "/" in talker_name or "\\" in talker_name:
        raise ValueError(f"Invalid talker name: {talker_name}")

    root = talkers_root or DATA_DIR
    talker_dir = root / talker_name
    talker_dir.mkdir(parents=True, exist_ok=True)

    create_time = video_info.get("create_time", 0)
    date_str = (
        datetime.fromtimestamp(create_time).strftime("%Y-%m-%d")
        if create_time
        else datetime.now().strftime("%Y-%m-%d")
    )

    desc = video_info.get("desc", "").strip()
    if not desc:
        raise FetchError("Video desc is empty — nothing to save")

    lines = desc.split("\n")
    title = lines[0][:60]
    content = "\n".join(lines)  # keep full desc as content

    file_path = talker_dir / f"{date_str}.md"

    if file_path.exists():
        with open(file_path, "a", encoding="utf-8") as f:
            f.write(f"\n## {title}\n{content}\n")
    else:
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(f"# {date_str}\n\n## {title}\n{content}\n")

    return file_path
