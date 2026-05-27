#!/usr/bin/env python3
"""
批量调用豆包 — 入口脚本
=======================

用法:
  python scripts/batch_doubao.py [talker_name] [options]

示例:
  python scripts/batch_doubao.py              # 处理所有 talker
  python scripts/batch_doubao.py talker1     # 仅处理 talker1
  python scripts/batch_doubao.py talker1 --max 5    # 最多 5 个
  python scripts/batch_doubao.py talker1 --force    # 强制重跑已转录的

前置条件:
  1. 豆包桌面客户端已打开并登录
  2. 已安装依赖: pip install pyautogui pywin32 pyperclip opencv-python Pillow
  3. data/talkers/ 下有至少一个 talker 目录，且 README.md 包含抖音主页链接
"""

import argparse
import logging
import sys
from pathlib import Path

# 确保项目根目录在 sys.path 中
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from financy_talk.scrapers.doubao import (
    find_doubao_window,
    process_talker,
)
from financy_talk.config import DATA_DIR

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("batch_doubao")


def list_talkers(talkers_root: Path) -> list[str]:
    """列出 data/talkers/ 下所有有效的 talker 目录。"""
    if not talkers_root.exists():
        return []
    talkers = []
    for d in sorted(talkers_root.iterdir()):
        if d.is_dir() and (d / "README.md").exists():
            talkers.append(d.name)
    return talkers


def main():
    parser = argparse.ArgumentParser(
        description="批量调用豆包桌面客户端提取抖音视频逐字文字稿",
    )
    parser.add_argument(
        "talker",
        nargs="?",
        default=None,
        help="要处理的 talker 名称 (不填则处理所有)",
    )
    parser.add_argument(
        "--max",
        type=int,
        default=10,
        help="每个 talker 最多处理的视频数 (默认 10)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="模拟运行，不实际发送请求到豆包",
    )
    parser.add_argument(
        "--data-dir",
        type=str,
        default=None,
        help="talkers 数据目录 (默认使用项目 data/talkers/)",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="强制重新处理已转录的视频",
    )
    args = parser.parse_args()

    talkers_root = Path(args.data_dir) if args.data_dir else DATA_DIR

    # 确定要处理的 talker 列表
    if args.talker:
        talker_list = [args.talker]
    else:
        talker_list = list_talkers(talkers_root)
        if not talker_list:
            logger.error(f"在 {talkers_root} 下未找到任何 talker 目录！")
            print(f"\n请先在 {talkers_root} 下创建 talker 目录，并在其中创建 README.md。")
            sys.exit(1)

    logger.info(f"待处理 talker: {talker_list}")
    logger.info(f"数据目录: {talkers_root}")

    # 检查豆包窗口 (dry-run 时跳过)
    if not args.dry_run:
        hwnd = find_doubao_window()
        if hwnd is None:
            print("\n" + "!" * 60)
            print("  未找到豆包窗口！")
            print("  请先手动打开豆包桌面客户端并登录。")
            print("!" * 60)
            sys.exit(1)
        logger.info(f"找到豆包窗口 (hwnd={hwnd})")

    # 逐个处理
    results = {}
    for name in talker_list:
        logger.info(f"===== 开始处理 talker: {name} =====")
        try:
            process_talker(
                talker_name=name,
                talkers_root=talkers_root,
                max_videos=args.max,
                dry_run=args.dry_run,
                force=args.force,
            )
            results[name] = "OK"
        except Exception as e:
            logger.error(f"处理 talker [{name}] 失败: {e}")
            results[name] = f"FAIL: {e}"

    # 汇总
    print("\n" + "=" * 50)
    print("处理完成，结果汇总:")
    print("=" * 50)
    for name, status in results.items():
        tag = "✓" if status == "OK" else "✗"
        print(f"  {tag} {name}: {status}")
    print("=" * 50)


if __name__ == "__main__":
    main()
