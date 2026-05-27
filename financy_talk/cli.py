"""CLI entry point for financy-talk."""
import sys
from datetime import date

import click

from financy_talk.config import get_api_key, ConfigError
from financy_talk.data.loader import (
    load_talker_transcripts, list_talkers, parse_trust_scores,
)
from financy_talk.ai.analyzer import analyze_talker
from financy_talk.ai.aggregator import aggregate_talkers
from financy_talk.output.reporter import format_report, save_report
from financy_talk.data.kb_builder import build_kb, load_kb
from financy_talk.data.digest import digest_transcripts


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

    click.echo(f"正在分析 {name} ({len(transcripts)} 篇文案)...")
    try:
        _ = get_api_key()
    except ConfigError as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)

    kb = load_kb(name)
    trust_scores = parse_trust_scores(name)
    if kb:
        click.echo(f"  已加载知识库 ({len(kb.nodes)} 个行业节点)")

    try:
        result = analyze_talker(name, transcripts, kb=kb, trust_scores=trust_scores)
    except Exception as e:
        click.echo(f"AI analysis failed: {e}", err=True)
        sys.exit(1)

    today = date.today().isoformat()
    formatted = format_report(result, talker_name=name, date=today)
    click.echo(formatted)
    try:
        path = save_report(formatted, talker_name=name, date=today)
    except ValueError as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)
    click.echo(f"\n报告已保存到：{path}")


@main.command()
@click.argument("names", nargs=-1, required=True)
def compare(names: tuple[str, ...]):
    """对比多个 talker 的观点，生成综合研判报告。"""
    if len(names) < 2:
        click.echo("Error: 至少需要两个 talker 进行对比。", err=True)
        sys.exit(1)

    talkers_data: dict[str, list] = {}
    kbs: dict = {}
    trust_map: dict = {}
    for name in names:
        try:
            talkers_data[name] = load_talker_transcripts(name)
        except FileNotFoundError as e:
            click.echo(f"Error: {e}", err=True)
            sys.exit(1)
        kb = load_kb(name)
        if kb:
            kbs[name] = kb
        ts = parse_trust_scores(name)
        if ts:
            trust_map[name] = ts

    total = sum(len(t) for t in talkers_data.values())
    click.echo(f"正在对比 {', '.join(names)} ({total} 篇文案)...")

    try:
        _ = get_api_key()
    except ConfigError as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)

    try:
        result = aggregate_talkers(talkers_data, kbs=kbs, trust_scores_map=trust_map)
    except Exception as e:
        click.echo(f"AI analysis failed: {e}", err=True)
        sys.exit(1)

    today = date.today().isoformat()
    formatted = format_report(result, talker_name="comparison", date=today)
    click.echo(formatted)
    try:
        path = save_report(formatted, talker_name="comparison", date=today)
    except ValueError as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)
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
        except FileNotFoundError:
            count = 0
        ts = parse_trust_scores(t)
        kb = load_kb(t)
        extra = []
        if ts:
            extra.append(f"信任: 短{ts.short_term}/中{ts.mid_term}/长{ts.long_term}")
        if kb:
            extra.append(f"KB: {len(kb.nodes)}节点")
        tag = " | ".join(extra)
        click.echo(f"  - {t} ({count} 篇文案)" + (f" [{tag}]" if tag else ""))


@main.command("digest")
@click.argument("name")
@click.option("--force", is_flag=True, help="强制重新处理所有文案")
def digest_command(name: str, force: bool):
    """对每篇文案做 AI 清洗：去除口语化、提炼关键信息点。"""
    click.echo(f"正在清洗文案: {name}...")
    try:
        _ = get_api_key()
    except ConfigError as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)

    try:
        count = digest_transcripts(name, force=force)
    except Exception as e:
        click.echo(f"Digest failed: {e}", err=True)
        sys.exit(1)

    if count == 0:
        click.echo("所有文案均已清洗，无需重复处理。")
    else:
        click.echo(f"完成！已清洗 {count} 篇文案 → data/talkers/{name}/digest/")


@main.command("build-kb")
@click.argument("name")
@click.option("--all", "rebuild_all", is_flag=True, help="从全部历史文案重建知识库（默认只处理最近5天）")
def build_kb_command(name: str, rebuild_all: bool):
    """从近期文案提取行业观点，构建/更新知识库。"""
    click.echo(f"正在{'重建' if rebuild_all else '更新'}知识库: {name}...")
    try:
        _ = get_api_key()
    except ConfigError as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)

    try:
        kb = build_kb(name, rebuild_all=rebuild_all)
    except Exception as e:
        click.echo(f"KB build failed: {e}", err=True)
        sys.exit(1)

    click.echo(f"知识库已保存 ({len(kb.nodes)} 个行业节点):")
    for node_name, node in kb.nodes.items():
        count = len(node.evidence)
        click.echo(f"  - {node_name} [{node.trend}] {node.core_claim[:60]}... ({count} 条论据)")
