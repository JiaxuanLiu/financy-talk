"""Extract video text from Douyin share links."""
import json
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


def _extract_aweme_json(html: str, video_id: str) -> dict:
    """Extract the embedded aweme JSON object from page HTML using
    balanced-brace matching.
    """
    marker = f'"aweme_id":"{video_id}"'
    idx = html.find(marker)
    if idx == -1:
        raise FetchError(
            f"无法获取视频数据（可能是反爬限制），请稍后重试。video_id={video_id}"
        )

    brace_start = html.rfind("{", 0, idx)
    if brace_start == -1:
        raise FetchError(f"解析视频数据失败。video_id={video_id}")

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
        return json.loads(raw)
    except json.JSONDecodeError:
        raise FetchError(f"解析视频数据失败。video_id={video_id}")


def _aweme_to_video_info(aweme: dict) -> dict:
    """Convert raw aweme JSON to the simplified video-info dict."""
    return {
        "desc": aweme.get("desc", ""),
        "author": (aweme.get("author") or {}).get("nickname", ""),
        "create_time": aweme.get("create_time", 0),
    }


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

    aweme = _extract_aweme_json(html, video_id)
    return _aweme_to_video_info(aweme)


def fetch_video_infos_batch(video_ids: list[str]) -> list[dict]:
    """Fetch full video info for multiple video IDs in a single browser session."""
    results: list[dict] = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent=MOBILE_UA,
            viewport={"width": 390, "height": 844},
        )
        page = context.new_page()

        for video_id in video_ids:
            try:
                video_url = f"https://www.douyin.com/video/{video_id}"
                page.goto(video_url, wait_until="networkidle", timeout=30000)
                page.wait_for_timeout(3000)
                html = page.content()
                aweme = _extract_aweme_json(html, video_id)
                info = _aweme_to_video_info(aweme)
                info["aweme_id"] = video_id
                results.append(info)
            except FetchError:
                continue

        browser.close()

    return results


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


# ---------------------------------------------------------------------------
# User profile / post-list functions
# ---------------------------------------------------------------------------

def extract_sec_uid(profile_url: str) -> str:
    """Extract sec_uid from a Douyin user profile link."""
    with httpx.Client(follow_redirects=False, timeout=15) as client:
        response = client.get(profile_url, headers={"User-Agent": MOBILE_UA})
        if response.status_code >= 400:
            response.raise_for_status()

    location = response.headers.get("location", "")
    match = re.search(r"/user/([A-Za-z0-9_]+)", location)
    if not match:
        raise FetchError(
            f"无法从跳转链接中提取用户ID，请确认是抖音用户主页链接。跳转: {location}"
        )
    return match.group(1)


def fetch_user_posts(sec_uid: str, max_count: int = 10) -> list[dict]:
    """Open the user profile page and capture the /aweme/post/ API
    response to get the latest video descs and IDs.
    """
    profile_url = f"https://www.douyin.com/user/{sec_uid}"

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent=MOBILE_UA,
            viewport={"width": 390, "height": 844},
        )
        page = context.new_page()

        post_data: list = []

        def on_response(response):
            if response.ok and "application/json" in (response.headers.get("content-type", "") or ""):
                try:
                    data = response.json()
                    if "aweme_list" in data:
                        post_data.append(data)
                except Exception:
                    pass

        page.on("response", on_response)
        page.goto(profile_url, wait_until="networkidle", timeout=30000)
        page.wait_for_timeout(5000)
        browser.close()

    if not post_data:
        raise FetchError(f"无法获取用户 {sec_uid} 的视频列表（可能是反爬限制）")

    items: list[dict] = []
    for data in post_data:
        for item in data.get("aweme_list", []):
            items.append({
                "aweme_id": str(item.get("aweme_id", "")),
                "desc": item.get("desc", ""),
            })

    return items[:max_count]


# ---------------------------------------------------------------------------
# Extracted-ID tracking (dedup)
# ---------------------------------------------------------------------------

def _tracking_file(talker_name: str, talkers_root: Path | None = None) -> Path:
    root = talkers_root or DATA_DIR
    return root / talker_name / ".extracted.json"


def load_extracted_ids(talker_name: str, talkers_root: Path | None = None) -> set[str]:
    """Return the set of already-extracted video IDs for a talker."""
    tf = _tracking_file(talker_name, talkers_root)
    if not tf.exists():
        return set()
    try:
        data = json.loads(tf.read_text(encoding="utf-8"))
        return set(data.get("video_ids", []))
    except Exception:
        return set()


def save_extracted_ids(
    talker_name: str,
    new_ids: set[str],
    talkers_root: Path | None = None,
) -> None:
    """Merge new_ids into the tracking file."""
    tf = _tracking_file(talker_name, talkers_root)
    existing = load_extracted_ids(talker_name, talkers_root)
    merged = existing | new_ids
    tf.parent.mkdir(parents=True, exist_ok=True)
    tf.write_text(
        json.dumps(
            {"video_ids": sorted(merged), "updated": datetime.now().isoformat()},
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )


# ---------------------------------------------------------------------------
# README parser
# ---------------------------------------------------------------------------

def parse_readme_for_profile_url(talker_name: str, talkers_root: Path | None = None) -> str:
    """Extract the Douyin profile URL from a talker's README.md.
    Finds the first douyin.com URL in the file — works regardless of
    whether the label uses Chinese, English, or any other characters.
    """
    root = talkers_root or DATA_DIR
    readme_path = root / talker_name / "README.md"
    if not readme_path.exists():
        raise FetchError(f"{talker_name} 的 README.md 不存在，请先创建。")

    text = readme_path.read_text(encoding="utf-8")

    # Find any douyin.com URL in the file
    m = re.search(r"https?://[^\s)]*douyin\.com/[^\s)]+", text)
    if m:
        return m.group(0)

    raise FetchError(
        f"无法从 {talker_name} 的 README.md 中找到抖音主页链接。"
        f"请确保 README 中包含类似 v.douyin.com/xxx 或 douyin.com/user/xxx 的链接。"
    )
