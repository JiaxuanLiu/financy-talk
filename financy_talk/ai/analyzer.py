"""Single-talker analysis via OpenAI API."""
from financy_talk.data.loader import TalkerTranscript, TrustScores, split_by_time_window
from financy_talk.data.kb_schema import KnowledgeBase
from financy_talk.config import get_model_config, get_api_key, DEEPSEEK_BASE_URL

SYSTEM_PROMPT = """你是一位资深财经分析师。请根据以下财经博主近期的视频文案和历史知识库，完成以下分析：

1. **核心观点总结**：提炼该博主近期表达的核心观点
2. **产业趋势分析**：根据其观点，汇总对应的产业趋势
3. **股市研判**：基于以上分析，对当前A股/港股相关板块做出研判建议

最近的短期观点（5天内）应作为决策核心依据，知识库用于验证趋势持续性。

请用中文输出。格式简洁清晰。"""


def analyze_talker(
    name: str,
    transcripts: list[TalkerTranscript],
    client: "OpenAI | None" = None,
    kb: KnowledgeBase | None = None,
    trust_scores: TrustScores | None = None,
) -> str:
    model_config = get_model_config("sonnet")

    if client is None:
        from openai import OpenAI
        client = OpenAI(api_key=get_api_key(), base_url=DEEPSEEK_BASE_URL, timeout=120)

    user_content = _build_user_prompt(name, transcripts, kb=kb, trust_scores=trust_scores)

    response = client.chat.completions.create(
        model=model_config.model,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_content},
        ],
        temperature=0.7,
        max_tokens=model_config.max_tokens,
        timeout=120,
    )
    content = response.choices[0].message.content
    if content is None:
        raise RuntimeError("API returned empty response (possible content filter)")
    return content


def _build_user_prompt(
    name: str,
    transcripts: list[TalkerTranscript],
    *,
    kb: KnowledgeBase | None = None,
    trust_scores: TrustScores | None = None,
) -> str:
    short, mid, long_list = split_by_time_window(transcripts)

    parts = [f"博主：{name}\n"]

    # Trust score hint
    if trust_scores:
        parts.append(
            f"博主信任评估：短期 {trust_scores.short_term} 分 | "
            f"中期 {trust_scores.mid_term} 分 | "
            f"长期 {trust_scores.long_term} 分"
        )
        best = max(
            ("短期", trust_scores.short_term),
            ("中期", trust_scores.mid_term),
            ("长期", trust_scores.long_term),
            key=lambda x: x[1],
        )
        parts.append(f"注意：该博主{best[0]}判断力最强 ({best[1]} 分)。\n")

    # Layer 1: KB background (long-term: 20-180 days, and mid-term evidence)
    if kb and kb.nodes:
        parts.append("---")
        parts.append("# 知识库积累（6个月内历史观点提炼）\n")
        for node_name, node in kb.nodes.items():
            parts.append(f"## {node_name}")
            parts.append(f"核心判断：{node.core_claim}")
            parts.append(f"趋势方向：{node.trend} | 置信度：{node.confidence}")
            if node.evidence:
                sorted_ev = sorted(node.evidence, key=lambda e: e.date, reverse=True)[:5]
                parts.append("关键论据：")
                for ev in sorted_ev:
                    parts.append(f"  - {ev.date}: {ev.point}")
            parts.append("")
        parts.append("---\n")

    # Layer 2: Mid-term summary (5-20 days)
    if mid and not kb:
        # Only include mid as summary if no KB exists; otherwise KB covers it
        parts.append("# 中期趋势参考（5-20天前）")
        for t in mid:
            parts.append(f"## {t.date}")
            for entry in t.entries:
                summary = entry.content[:120] + "..." if len(entry.content) > 120 else entry.content
                parts.append(f"- {entry.title}: {summary}")
        parts.append("---\n")

    # Layer 3: Short-term full text (0-5 days) — decision core
    if short:
        parts.append("# 最新观点（5天内，决策核心）\n")
        for t in short:
            parts.append(f"## {t.date}")
            for entry in t.entries:
                parts.append(f"### {entry.title}")
                parts.append(entry.content)
                parts.append("")
    elif mid:
        # Fallback: no short-term transcripts, use mid as primary
        parts.append("# 近期观点（无5天内新内容，以下为最新可用文案）\n")
        for t in mid:
            parts.append(f"## {t.date}")
            for entry in t.entries:
                parts.append(f"### {entry.title}")
                parts.append(entry.content)
                parts.append("")
    else:
        # No short or mid — fall back to flat dump of all transcripts
        for t in transcripts:
            parts.append(f"## {t.date}")
            for entry in t.entries:
                parts.append(f"### {entry.title}")
                parts.append(entry.content)
                parts.append("")

    return "\n".join(parts)
