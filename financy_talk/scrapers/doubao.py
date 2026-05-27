"""
豆包桌面客户端自动化 — 通过 UI 自动化让豆包提取抖音视频逐字文字稿。

核心流程 (process_video):
  1. 找到并激活豆包窗口
  2. 点击「专家」模式入口 (如果尚未在专家对话中)
  3. 点击输入框 → 粘贴提示词 → 回车发送
  4. 等待豆包回复完成 (通过检测剪贴板内容稳定)
  5. 复制回复文本返回

坐标校准:
  运行 python -m financy_talk.scrapers.doubao --calibrate
  会交互式地让你手动点击 UI 元素，自动记录坐标到 doubao_config.json。
"""

import argparse
import json
import logging
import time
import warnings
from datetime import datetime
from pathlib import Path

import pyautogui
import pyperclip
import win32con
import win32gui
from PIL import ImageGrab

warnings.filterwarnings("ignore", category=DeprecationWarning, module="pyautogui")

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# 配置
# ---------------------------------------------------------------------------

DOUBAO_WINDOW_TITLE = "豆包"

# 超时配置 (秒)
PHASE1_TIMEOUT = 180         # 最长等待豆包"开始回复"的时间 (视频处理可能很慢)
PHASE2_TIMEOUT = 300         # 豆包开始回复后，最长等待"写完"的时间
POLL_INTERVAL = 3            # 截图轮询间隔
STABLE_ROUNDS = 3            # 连续 N 轮截图不变 → 回复完成
SEND_INTERVAL = 5            # 两个视频之间的间隔
# 截图检测区域 (相对于 response_region 点的矩形)
SCREENSHOT_W = 400
SCREENSHOT_H = 300

# 配置文件路径
CONFIG_PATH = (
    Path(__file__).resolve().parent.parent.parent
    / "data" / "reference_images" / "doubao_config.json"
)

# 默认坐标 (用户需要通过 calibrate 模式校准)
# 所有坐标均为相对于豆包窗口客户区左上角的 (x, y)
DEFAULT_CONFIG = {
    "window_title": "豆包",
    "expert_btn": None,        # (x, y) 底部工具栏模式切换按钮
    "expert_dropdown": None,   # (x, y) 下拉菜单中「专家」选项
    "new_chat_btn": None,      # (x, y) 新建对话按钮
    "input_field": None,       # (x, y) 输入框
    "send_btn": None,          # (x, y) 发送按钮 (可选，用 Enter 代替)
    "response_region": None,   # [x, y] 回复区域坐标
    "calibrated": False,
    "note": "请用 --calibrate 模式校准坐标",
}


# ---------------------------------------------------------------------------
# 配置 I/O
# ---------------------------------------------------------------------------

def load_config() -> dict:
    if CONFIG_PATH.exists():
        try:
            return json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
        except Exception:
            pass
    save_config(DEFAULT_CONFIG)
    return dict(DEFAULT_CONFIG)


def save_config(cfg: dict) -> None:
    CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    CONFIG_PATH.write_text(
        json.dumps(cfg, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


# ---------------------------------------------------------------------------
# 窗口管理
# ---------------------------------------------------------------------------

def find_doubao_window() -> int | None:
    """查找豆包主窗口 hwnd。"""
    # 策略 1: 精确标题匹配
    hwnd = win32gui.FindWindow(None, DOUBAO_WINDOW_TITLE)
    if hwnd and win32gui.IsWindowVisible(hwnd):
        rect = win32gui.GetWindowRect(hwnd)
        w = rect[2] - rect[0]
        h = rect[3] - rect[1]
        if w > 400 and h > 400:
            return hwnd

    # 策略 2: 模糊匹配
    result = []

    def callback(h, _):
        if win32gui.IsWindowVisible(h):
            try:
                title = win32gui.GetWindowText(h)
                if "豆包" in title or "Doubao" in title:
                    rect = win32gui.GetWindowRect(h)
                    w_ = rect[2] - rect[0]
                    h_ = rect[3] - rect[1]
                    if w_ > 400 and h_ > 400:
                        result.append(h)
            except Exception:
                pass

    win32gui.EnumWindows(callback, None)
    return result[0] if result else None


def activate_window(hwnd: int) -> None:
    """恢复（如最小化）并置前窗口。

    使用 AttachThreadInput 绕过 SetForegroundWindow 的权限限制。
    """
    import ctypes

    # 恢复最小化窗口
    if win32gui.IsIconic(hwnd):
        win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
        time.sleep(0.4)

    # 先放到最上层
    win32gui.SetWindowPos(
        hwnd, win32con.HWND_TOP, 0, 0, 0, 0,
        win32con.SWP_NOMOVE | win32con.SWP_NOSIZE | win32con.SWP_SHOWWINDOW,
    )
    time.sleep(0.1)

    # AttachThreadInput: 让我们的线程能控制窗口线程的输入
    foreground_hwnd = win32gui.GetForegroundWindow()
    current_thread = ctypes.windll.kernel32.GetCurrentThreadId()
    target_thread = ctypes.windll.user32.GetWindowThreadProcessId(hwnd, None)

    attached = False
    if foreground_hwnd and foreground_hwnd != hwnd:
        fg_thread = ctypes.windll.user32.GetWindowThreadProcessId(
            foreground_hwnd, None
        )
        if fg_thread != current_thread:
            ctypes.windll.user32.AttachThreadInput(
                current_thread, fg_thread, True
            )
            attached = True

    try:
        win32gui.BringWindowToTop(hwnd)
        win32gui.SetForegroundWindow(hwnd)
    except Exception:
        pass  # 静默忽略, pyautogui 仍可能工作
    finally:
        if attached:
            ctypes.windll.user32.AttachThreadInput(
                current_thread,
                ctypes.windll.user32.GetWindowThreadProcessId(
                    foreground_hwnd, None
                ),
                False,
            )

    time.sleep(0.3)


def get_client_rect(hwnd: int) -> tuple[int, int, int, int]:
    """获取窗口客户区 (不含标题栏/边框) 的屏幕坐标。

    Returns: (left, top, right, bottom) 屏幕绝对坐标。
    """
    import ctypes
    from ctypes.wintypes import RECT, POINT

    # GetClientRect: 填充客户区相对于自身的坐标 (0,0,width,height)
    client = RECT()
    ctypes.windll.user32.GetClientRect(hwnd, ctypes.byref(client))

    # ClientToScreen: 将客户区左上角 (0,0) 转为屏幕坐标
    top_left = POINT(client.left, client.top)
    ctypes.windll.user32.ClientToScreen(hwnd, ctypes.byref(top_left))

    # 右下角
    rb = POINT(client.right, client.bottom)
    ctypes.windll.user32.ClientToScreen(hwnd, ctypes.byref(rb))

    return (top_left.x, top_left.y, rb.x, rb.y)


def rel_to_abs(hwnd: int, rel_x: int, rel_y: int) -> tuple[int, int]:
    """将窗口客户区相对坐标转换为屏幕绝对坐标。"""
    cl = get_client_rect(hwnd)
    return cl[0] + rel_x, cl[1] + rel_y


# ---------------------------------------------------------------------------
# 交互底层
# ---------------------------------------------------------------------------

def click_rel(hwnd: int, rel_x: int, rel_y: int, pause: float = 0.3) -> None:
    """点击窗口客户区相对坐标。"""
    abs_x, abs_y = rel_to_abs(hwnd, rel_x, rel_y)
    pyautogui.click(abs_x, abs_y)
    time.sleep(pause)


def paste_text(text: str) -> None:
    """将文本粘贴到当前焦点位置。"""
    pyperclip.copy(text)
    time.sleep(0.15)
    pyautogui.hotkey("ctrl", "v")
    time.sleep(0.2)


def send_text_to_input(hwnd: int, text: str, input_coord: tuple) -> None:
    """点击输入框 → 清空 → 粘贴文本 → 回车发送。"""
    rx, ry = input_coord
    click_rel(hwnd, rx, ry, pause=0.2)
    # 全选清空
    pyautogui.hotkey("ctrl", "a")
    time.sleep(0.05)
    pyautogui.press("delete")
    time.sleep(0.05)
    # 粘贴
    paste_text(text)
    time.sleep(0.2)
    # 发送
    pyautogui.press("enter")


# ---------------------------------------------------------------------------
# 等待回复完成 — 截图比对，零点击轮询
# ---------------------------------------------------------------------------

def _screenshot_hash(hwnd: int, response_coord: tuple) -> int:
    """截取豆包窗口回复区域的像素 hash，用于检测内容变化。"""
    cl = get_client_rect(hwnd)
    rx, ry = response_coord
    x = cl[0] + rx - SCREENSHOT_W // 2
    y = cl[1] + ry - SCREENSHOT_H // 2
    # 确保坐标合法
    x = max(cl[0], min(x, cl[2] - SCREENSHOT_W))
    y = max(cl[1], min(y, cl[3] - SCREENSHOT_H))
    try:
        img = ImageGrab.grab(bbox=(x, y, x + SCREENSHOT_W, y + SCREENSHOT_H))
        # 缩放后 hash，提高性能且容忍微小变化
        small = img.resize((40, 30))
        return hash(small.tobytes())
    except Exception:
        return 0


def wait_for_response(
    hwnd: int,
    response_coord: tuple | None = None,
    sent_prompt: str = "",
    phase1_timeout: int = PHASE1_TIMEOUT,
    phase2_timeout: int = PHASE2_TIMEOUT,
) -> str:
    """等待豆包回复完成 — 两阶段截图检测。

    阶段 1: 等待豆包「开始打字」
      - 发送后回复区域可能长时间无变化 (豆包在后台看视频/思考)
      - 每 POLL_INTERVAL 秒截图，与基线比对
      - 截图一旦发生变化 → 豆包开始回复了，进入阶段 2
      - 超过 phase1_timeout 仍无变化 → 可能豆包卡住了，强制提取

    阶段 2: 等待豆包「打完字」
      - 继续截图比对
      - 连续 STABLE_ROUNDS 轮 hash 不变 → 回复完成
      - 超过 phase2_timeout → 强制提取

    全程不点击不复制，只在最后点一次提取回复文本。
    """
    logger.info(
        f"等待豆包回复 (阶段1最多{phase1_timeout}s, 阶段2最多{phase2_timeout}s)..."
    )

    if response_coord is None:
        logger.warning("未配置 response_region，用固定 120s 等待")
        time.sleep(120)
        cl = get_client_rect(hwnd)
        cx = (cl[0] + cl[2]) // 2
        cy = (cl[1] + cl[3]) // 2
        pyautogui.click(cx, cy)
        time.sleep(0.3)
        return _copy_all_and_extract(sent_prompt)

    # --- 采集基线截图 (等 3s 让消息先出现在画面上) ---
    time.sleep(3)
    baseline_hash = _screenshot_hash(hwnd, response_coord)

    # ═══════════════════════════════════
    # 阶段 1: 等待豆包开始回复
    # ═══════════════════════════════════
    logger.info("  阶段1: 等待豆包开始回复...")
    deadline1 = time.time() + phase1_timeout
    response_started = False

    while time.time() < deadline1:
        cur_hash = _screenshot_hash(hwnd, response_coord)
        if cur_hash != baseline_hash and cur_hash != 0:
            logger.info(f"  豆包开始回复了! (耗时 {time.time() - (deadline1 - phase1_timeout):.0f}s)")
            response_started = True
            break
        time.sleep(POLL_INTERVAL)

    if not response_started:
        logger.warning(f"  阶段1超时 ({phase1_timeout}s)，豆包可能未响应，强制提取")
        rx, ry = response_coord
        click_rel(hwnd, rx, ry, pause=0.5)
        return _copy_all_and_extract(sent_prompt)

    # ═══════════════════════════════════
    # 阶段 2: 等待豆包写完
    # ═══════════════════════════════════
    logger.info("  阶段2: 等待豆包写完...")
    deadline2 = time.time() + phase2_timeout
    last_hash = cur_hash   # 从阶段1最后的hash继续
    stable = 0

    while time.time() < deadline2:
        cur_hash = _screenshot_hash(hwnd, response_coord)
        if cur_hash == last_hash and cur_hash != 0:
            stable += 1
            if stable >= STABLE_ROUNDS:
                logger.info(f"  豆包写完了! (稳定{STABLE_ROUNDS}轮, 阶段2耗时 {time.time() - (deadline2 - phase2_timeout):.0f}s)")
                break
        else:
            stable = 0
        last_hash = cur_hash
        time.sleep(POLL_INTERVAL)

    if time.time() >= deadline2:
        logger.warning(f"  阶段2超时 ({phase2_timeout}s)，强制提取")

    # --- 点击一次 → 全选 → 复制 → 提取 ---
    rx, ry = response_coord
    click_rel(hwnd, rx, ry, pause=0.5)
    return _copy_all_and_extract(sent_prompt)


def _copy_all_and_extract(sent_prompt: str) -> str:
    """全选聊天内容 → 复制 → 从中提取豆包的回复部分。

    策略: 从剪贴板中找 sent_prompt 最后出现位置，
          取其后的内容作为回复。如果找不到 sent_prompt，
          则返回全部内容（可能是新会话没有历史）。
    """
    # 全选 + 复制
    pyautogui.hotkey("ctrl", "a")
    time.sleep(0.1)
    pyautogui.hotkey("ctrl", "c")
    time.sleep(0.3)

    full_text = pyperclip.paste().strip()

    if not full_text:
        return ""

    # 尝试从全文里找出我们发送的提示词，取其后的内容
    # 用 URL 特征定位更准确（提示词包含 douyin.com）
    if sent_prompt and sent_prompt in full_text:
        idx = full_text.rfind(sent_prompt)
        after = full_text[idx + len(sent_prompt):].strip()
        # 如果"之后"的内容太短，说明 Ctrl+A 没选全
        if len(after) > 20:
            return after

    # Fallback: 尝试找 douyin.com URL 作为分割点
    if "douyin.com" in full_text:
        idx = full_text.rfind("douyin.com")
        # 跳到 URL 之后
        end_of_url = full_text.find("\n", idx)
        if end_of_url > 0 and len(full_text[end_of_url:].strip()) > 20:
            return full_text[end_of_url:].strip()

    # 终极兜底: 全返回（可能包含提示词，但至少不会丢失内容）
    logger.warning("无法精确提取回复文本，返回全部剪贴板内容")
    return full_text


# ---------------------------------------------------------------------------
# 专家模式切换
# ---------------------------------------------------------------------------

def ensure_expert_mode(hwnd: int, cfg: dict) -> None:
    """确保当前豆包窗口处于专家模式。

    豆包 UI 布局 (底部工具栏):
      [专家] [AI播客] [超能模式] [联网搜索] [搜索] ...

    流程:
      1. 点击底部工具栏的模式切换按钮 (显示为当前模式名)
      2. 等待下拉菜单出现 (快速/思考/专家)
      3. 如果有 expert_dropdown 坐标 → 点击「专家」
      4. 如果只有 expert_btn → 仅点击模式切换 (如果已是专家，无影响)

    如果未经校准或豆包已处于专家模式，此函数无副作用。
    """
    expert_btn = cfg.get("expert_btn")
    expert_dropdown = cfg.get("expert_dropdown")

    if not expert_btn:
        logger.info("未配置 expert_btn 坐标，跳过专家模式切换 (请确保豆包已处于专家模式)")
        return

    logger.info("切换专家模式...")
    # Step 1: 点击底部工具栏的模式切换按钮
    rx, ry = expert_btn
    click_rel(hwnd, rx, ry, pause=0.5)
    time.sleep(1)  # 等待下拉菜单出现

    # Step 2: 如果配置了下拉菜单中的「专家」坐标，点击它
    if expert_dropdown:
        rx2, ry2 = expert_dropdown
        click_rel(hwnd, rx2, ry2, pause=0.3)
        time.sleep(1)
        logger.info("已选择「专家」模式")
    else:
        # 没有下拉坐标 → 点击模式切换后按 Escape 关闭下拉
        # (如果已是专家模式则无影响，如果不是则需要手动操作)
        pyautogui.press("escape")
        time.sleep(0.3)
        logger.warning(
            "未配置 expert_dropdown 坐标，无法自动选择「专家」选项。"
            "请确保已手动切换到专家模式，或重新运行 --calibrate 校准。"
        )


# ---------------------------------------------------------------------------
# 公共 API
# ---------------------------------------------------------------------------

def process_video(
    video_url: str,
    hwnd: int | None = None,
    prompt_template: str = "帮我提取这个抖音视频的逐字文字稿：{url}",
    cfg: dict | None = None,
    dry_run: bool = False,
) -> str:
    """对单个视频，让豆包提取逐字文字稿。

    Args:
        video_url: 抖音视频 URL
        hwnd: 豆包窗口 hwnd (不提供则自动查找)
        prompt_template: 提示词模板，{url} 会被替换为 video_url
        cfg: 配置 dict (不提供则自动从文件加载)
        dry_run: 模拟运行，不实际发送

    Returns:
        豆包返回的逐字文字稿文本。

    Raises:
        RuntimeError: 豆包窗口未找到或其他自动化失败。
    """
    if cfg is None:
        cfg = load_config()

    if hwnd is None:
        hwnd = find_doubao_window()
    if hwnd is None:
        raise RuntimeError(
            "未找到豆包窗口！请先手动打开豆包桌面客户端并登录。"
        )

    activate_window(hwnd)

    input_coord = cfg.get("input_field")
    response_coord = cfg.get("response_region")

    if not input_coord:
        raise RuntimeError(
            "未配置 input_field 坐标！请先运行 --calibrate 校准。"
        )

    prompt = prompt_template.format(url=video_url)
    logger.info(f"发送提示词: {prompt[:60]}...")

    if dry_run:
        logger.info("[DRY RUN] 跳过实际发送")
        return "(dry run)"

    # Step 1: 确保专家模式 (如果配置了)
    ensure_expert_mode(hwnd, cfg)

    # Step 2: 发送提示词
    send_text_to_input(hwnd, prompt, input_coord)

    # Step 3: 等待回复 (两阶段检测: 先等开始, 再等写完)
    response = wait_for_response(
        hwnd,
        response_coord=response_coord,
        sent_prompt=prompt,
        phase1_timeout=PHASE1_TIMEOUT,
        phase2_timeout=PHASE2_TIMEOUT,
    )

    if not response or len(response) < 10:
        logger.warning("回复内容过短，可能提取失败，重试...")
        time.sleep(2)
        rx, ry = response_coord or (500, 400)
        click_rel(hwnd, rx, ry, pause=0.5)
        response = _copy_all_and_extract(prompt)

    logger.info(f"提取完成，文字稿长度: {len(response)} 字符")
    return response


# ---------------------------------------------------------------------------
# 批量处理
# ---------------------------------------------------------------------------

def _transcribed_file(talker_dir: Path) -> Path:
    return talker_dir / ".transcribed.json"


def _load_transcribed_ids(talker_dir: Path) -> set[str]:
    tf = _transcribed_file(talker_dir)
    if not tf.exists():
        return set()
    try:
        data = json.loads(tf.read_text(encoding="utf-8"))
        return set(data.get("video_ids", []))
    except Exception:
        return set()


def _save_transcribed_ids(talker_dir: Path, new_ids: set[str]) -> None:
    from datetime import datetime
    tf = _transcribed_file(talker_dir)
    existing = _load_transcribed_ids(talker_dir)
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


def _save_transcript(
    talker_dir: Path,
    video_id: str,
    transcript: str,
    video_date: str = "",
    video_title: str = "",
) -> Path:
    """将逐字稿保存到按日期分组的 MD 文件。

    格式与现有 douyin.py 的 save_as_transcript 一致:
      # YYYY-MM-DD
      ## 视频标题
      逐字稿内容...
    同一日期的多个视频追加到同一文件。
    """
    if not video_date:
        from datetime import datetime
        video_date = datetime.now().strftime("%Y-%m-%d")

    if not video_title:
        video_title = f"视频 https://www.douyin.com/video/{video_id}"

    file_path = talker_dir / f"{video_date}.md"
    entry = f"\n## {video_title}\n\n{transcript}\n"

    if file_path.exists():
        with open(file_path, "a", encoding="utf-8") as f:
            f.write(entry)
    else:
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(f"# {video_date}\n")
            f.write(entry)

    logger.info(f"已保存: {file_path} ({video_date})")
    return file_path


def process_talker(
    talker_name: str,
    talkers_root: Path | None = None,
    max_videos: int = 10,
    dry_run: bool = False,
    force: bool = False,
) -> None:
    """处理单个 talker 的所有未转录视频。

    流程:
      1. 读取 .extracted.json 获取视频 ID
      2. 批量获取视频信息 (create_time, desc) 用于日期分组和标题
      3. 跳过已转录的视频 (除非 force=True)
      4. 逐个调用豆包提取逐字稿
      5. 按视频发布日期保存到 YYYY-MM-DD.md
    """
    from financy_talk.config import DATA_DIR
    from financy_talk.scrapers.douyin import (
        load_extracted_ids,
        fetch_video_infos_batch,
    )

    root = talkers_root or DATA_DIR
    talker_dir = root / talker_name
    if not talker_dir.exists():
        raise RuntimeError(f"talker 目录不存在: {talker_dir}")

    cfg = load_config()
    hwnd = find_doubao_window()
    if hwnd is None and not dry_run:
        raise RuntimeError("未找到豆包窗口！请先打开豆包。")

    if hwnd:
        activate_window(hwnd)

    # 读取视频 ID
    all_ids = load_extracted_ids(talker_name, root)

    # 已转录筛选
    if force:
        pending = sorted(all_ids)
        logger.info(f"[{talker_name}] 强制模式，处理全部 {len(pending)} 个视频")
    else:
        transcribed_ids = _load_transcribed_ids(talker_dir)
        pending = sorted(all_ids - transcribed_ids)

    if not pending:
        logger.info(f"[{talker_name}] 没有待转录的视频")
        return

    pending = pending[-max_videos:]  # 取最新的 max_videos 个
    logger.info(f"[{talker_name}] 待转录 {len(pending)} 个视频 (最新)")

    # --- 批量获取视频信息 (日期 + 标题) ---
    logger.info("[{talker_name}] 正在获取视频信息 (create_time, desc)...")
    video_map: dict[str, dict] = {}  # video_id -> {date, title}
    try:
        infos = fetch_video_infos_batch(pending)
        for info in infos:
            vid = info.get("aweme_id", "")
            create_ts = info.get("create_time", 0)
            desc = info.get("desc", "").strip()
            date_str = (
                datetime.fromtimestamp(create_ts).strftime("%Y-%m-%d")
                if create_ts
                else datetime.now().strftime("%Y-%m-%d")
            )
            # 标题: desc 第一行，限 60 字符
            title_line = desc.split("\n")[0][:60] if desc else ""
            video_map[vid] = {"date": date_str, "title": title_line}
        logger.info(f"[{talker_name}] 获取到 {len(video_map)} 条视频信息")
    except Exception as e:
        logger.warning(f"获取视频信息失败: {e}，将使用当天日期和 URL 作为标题")

    # --- 逐个转录 ---
    success_ids: set[str] = set()
    for vid in pending:
        url = f"https://www.douyin.com/video/{vid}"
        info = video_map.get(vid, {})
        vdate = info.get("date", "")
        vtitle = info.get("title", "")

        logger.info(f"  处理: {url}  [{vdate}] {vtitle[:30]}...")

        try:
            transcript = process_video(
                video_url=url,
                hwnd=hwnd,
                cfg=cfg,
                dry_run=dry_run,
            )
            # dry-run 不写入文件，但保留日志
            if not dry_run:
                _save_transcript(talker_dir, vid, transcript, vdate, vtitle)
            success_ids.add(vid)
        except Exception as e:
            logger.error(f"  失败: {e}")
            continue

        time.sleep(SEND_INTERVAL)

    if not dry_run:
        _save_transcribed_ids(talker_dir, success_ids)
    logger.info(f"[{talker_name}] 完成，成功 {len(success_ids)}/{len(pending)}")


# ---------------------------------------------------------------------------
# 坐标校准模式
# ---------------------------------------------------------------------------

def calibrate():
    """交互式坐标校准: 让用户在豆包窗口上点击，记录坐标。"""
    print("\n" + "=" * 60)
    print("  豆包 UI 坐标校准模式")
    print("=" * 60)
    print("\n说明: 程序会依次提示你点击豆包窗口上的各个 UI 元素，")
    print("      然后按 Enter 确认坐标。\n")

    hwnd = find_doubao_window()
    if hwnd is None:
        print("✗ 未找到豆包窗口！请先打开豆包客户端。")
        return

    activate_window(hwnd)
    client_rect = get_client_rect(hwnd)
    print(f"豆包窗口客户区: left={client_rect[0]}, top={client_rect[1]}")
    print(f"               size={client_rect[2]-client_rect[0]}x{client_rect[3]-client_rect[1]}")
    print()

    cfg = load_config()

    def _get_coord(prompt: str) -> tuple | None:
        """让用户手动移动鼠标到目标位置，按 Enter 记录。"""
        print(f"\n→ {prompt}")
        print("  请将鼠标移动到目标位置，然后按 Enter...")
        input("  按 Enter 当鼠标就位 > ")
        x, y = pyautogui.position()
        # 转换为相对坐标
        rel_x = x - client_rect[0]
        rel_y = y - client_rect[1]
        print(f"  绝对坐标: ({x}, {y})")
        print(f"  相对坐标: ({rel_x}, {rel_y})")
        ok = input("  确认使用这个坐标? [Y/n] > ").strip().lower()
        if ok in ("", "y", "yes"):
            return (rel_x, rel_y)
        return None

    print("\n豆包 UI 元素位置参考:")
    print("  ┌──────────────────────┐")
    print("  │                      │")
    print("  │   回复区域 (第4步)    │")
    print("  │                      │")
    print("  ├──────────────────────┤")
    print("  │   输入框 (第3步)      │")
    print("  ├──────────────────────┤")
    print("  │ [专家][快速][思考]   │  ← 模式切换 (第1步，底部工具栏)")
    print("  └──────────────────────┘")
    print()

    # 1. 专家模式按钮 — 底部工具栏
    print("第1步: 定位「专家」模式按钮")
    print("  说明: 豆包底部工具栏有模式切换按钮 (可能是「快速」/「思考」/「专家」)")
    print("  请将鼠标移到模式切换区域 (底部工具栏)，按 Enter 确认")
    result = _get_coord("将鼠标移到豆包底部工具栏的「模式切换」按钮上")
    if result:
        cfg["expert_btn"] = list(result)

    # 另外记录专家下拉项 (点击模式切换后出现)
    if input("\n是否还需要校准「专家」下拉选项的位置? [y/N] > ").strip().lower() in ("y", "yes"):
        result = _get_coord("将鼠标移到下拉菜单中的「专家」选项上")
        if result:
            cfg["expert_dropdown"] = list(result)

    # 2. 新建对话按钮 (可选)
    result = _get_coord("点击「新建对话」按钮 (可选)")
    if result:
        cfg["new_chat_btn"] = list(result)

    # 3. 输入框
    result = _get_coord("点击输入框 (豆包窗口底部，工具栏上方)")
    if result:
        cfg["input_field"] = list(result)

    # 4. 回复区域 (用于复制)
    result = _get_coord("点击豆包回复区域的任意位置 (中部聊天区域)")
    if result:
        cfg["response_region"] = list(result)

    cfg["calibrated"] = True
    cfg["note"] = f"校准于 {time.strftime('%Y-%m-%d %H:%M:%S')}"
    save_config(cfg)

    print("\n" + "=" * 60)
    print("  校准完成！坐标已保存到:")
    print(f"  {CONFIG_PATH}")
    print("=" * 60)
    print("\n校准结果:")
    print(json.dumps(cfg, ensure_ascii=False, indent=2))
    print()


# ---------------------------------------------------------------------------
# CLI 入口
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="豆包自动化 — 抖音视频逐字稿提取",
    )
    parser.add_argument(
        "--calibrate",
        action="store_true",
        help="进入交互式坐标校准模式",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="模拟运行，不实际发送",
    )
    parser.add_argument(
        "--talker",
        type=str,
        default=None,
        help="要处理的 talker 名称",
    )
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
    )

    if args.calibrate:
        calibrate()
        return

    if args.talker:
        process_talker(
            talker_name=args.talker,
            dry_run=args.dry_run,
        )
    else:
        print("请指定 --talker <name> 或 --calibrate")
        print("示例: python -m financy_talk.scrapers.doubao --calibrate")


if __name__ == "__main__":
    main()
