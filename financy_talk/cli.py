"""CLI entry point for financy-talk."""
import sys
from datetime import date

import click

from financy_talk.config import get_api_key, ConfigError
from financy_talk.data.loader import load_talker_transcripts, list_talkers
from financy_talk.ai.analyzer import analyze_talker
from financy_talk.ai.aggregator import aggregate_talkers
from financy_talk.output.reporter import format_report, save_report


@click.group()
def main():
    """Financy Talk — AI-powered financial talker transcript analysis."""


@main.command()
@click.argument("name")
def analyze(name: str):
    """分析单个 talker 的文案，生成趋势研判报告。"""
    try:
        transcripts = load_talker_transcripts(name)
    except FileNotFoundError as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)

    if not transcripts:
        click.echo(f"Talker '{name}' has no transcript files.")
        sys.exit(1)

    click.echo(f"正在分析 {name} ({len(transcripts)} 篇文案)...")
    try:
        _ = get_api_key()
    except ConfigError as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)

    try:
        result = analyze_talker(name, transcripts)
    except Exception as e:
        click.echo(f"AI analysis failed: {e}", err=True)
        sys.exit(1)

    today = date.today().isoformat()
    formatted = format_report(result, talker_name=name, date=today)
    click.echo(formatted)
    path = save_report(formatted, talker_name=name, date=today)
    click.echo(f"\n报告已保存到：{path}")


@main.command()
@click.argument("names", nargs=-1, required=True)
def compare(names: tuple[str, ...]):
    """对比多个 talker 的观点，生成综合研判报告。"""
    if len(names) < 2:
        click.echo("Error: 至少需要两个 talker 进行对比。", err=True)
        sys.exit(1)

    talkers_data: dict[str, list] = {}
    for name in names:
        try:
            talkers_data[name] = load_talker_transcripts(name)
        except FileNotFoundError as e:
            click.echo(f"Error: {e}", err=True)
            sys.exit(1)

    total = sum(len(t) for t in talkers_data.values())
    click.echo(f"正在对比 {', '.join(names)} ({total} 篇文案)...")

    try:
        _ = get_api_key()
    except ConfigError as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)

    try:
        result = aggregate_talkers(talkers_data)
    except Exception as e:
        click.echo(f"AI analysis failed: {e}", err=True)
        sys.exit(1)

    today = date.today().isoformat()
    formatted = format_report(result, talker_name="comparison", date=today)
    click.echo(formatted)
    path = save_report(formatted, talker_name="comparison", date=today)
    click.echo(f"\n报告已保存到：{path}")


@main.command("list")
def list_command():
    """列出所有已添加的 talker。"""
    talkers = list_talkers()
    if not talkers:
        click.echo("没有找到任何 talker。请在 data/talkers/ 下创建文件夹。")
        return
    click.echo("已添加的 Talker：")
    for t in talkers:
        try:
            transcripts = load_talker_transcripts(t)
            count = len(transcripts)
            click.echo(f"  - {t} ({count} 篇文案)")
        except FileNotFoundError:
            click.echo(f"  - {t} (0 篇文案)")
