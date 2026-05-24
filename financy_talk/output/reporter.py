"""Format and save analysis reports."""
from pathlib import Path

from financy_talk.config import OUTPUT_DIR


def format_report(content: str, talker_name: str, date: str) -> str:
    header = f"# Financy Talk — {talker_name} 分析报告\n\n**日期:** {date}\n\n---\n\n"
    return header + content


def save_report(content: str, *, talker_name: str, date: str, output_dir: Path | None = None) -> Path:
    base = output_dir or OUTPUT_DIR
    target_dir = base / talker_name
    target_dir.mkdir(parents=True, exist_ok=True)
    filename = f"{date}_report.md"
    path = target_dir / filename
    path.write_text(content, encoding="utf-8")
    return path
