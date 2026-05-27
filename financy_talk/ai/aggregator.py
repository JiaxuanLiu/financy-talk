"""Multi-talker comparison and aggregation via OpenAI API."""
from financy_talk.data.loader import TalkerTranscript, TrustScores, split_by_time_window
from financy_talk.data.kb_schema import KnowledgeBase
from financy_talk.config import get_model_config, get_api_key, DEEPSEEK_BASE_URL

COMPARISON_PROMPT = """你是一位资深财经分析师。以下是多位财经博主的近期观点汇总和历史知识库对比，请完成以下分析：

1. **各博主核心观点对比**：逐位总结核心观点，标注每位博主的信任评估
2. **异同分析**：找出观点的一致性与分歧
3. **产业趋势共识**：提炼多位博主共同关注的产业方向
4. **股市综合研判**：结合多方观点和每位博主的信任偏向，对当前A股/港股给出综合研判建议

最近短期观点应作为决策核心。当博主观点冲突时，优先参考对应时间尺度上信任评分更高的博主。

请用中文输出。格式简洁清晰。"""


def aggregate_talkers(
    talkers_data: dict[str, list[TalkerTranscript]],
    client: "OpenAI | None" = None,
    kbs: dict[str, KnowledgeBase] | None = None,
    trust_scores_map: dict[str, TrustScores] | None = None,
) -> str:
    model_config = get_model_config("opus")

    if client is None:
        from openai import OpenAI
        client = OpenAI(api_key=get_api_key(), base_url=DEEPSEEK_BASE_URL, timeout=120)

    user_content = _build_comparison_prompt(
        talkers_data, kbs=kbs, trust_scores_map=trust_scores_map,
    )

    response = client.chat.completions.create(
        model=model_config.model,
        messages=[
            {"role": "system", "content": COMPARISON_PROMPT},
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


def _build_comparison_prompt(
    talkers_data: dict[str, list[TalkerTranscript]],
    *,
    kbs: dict[str, KnowledgeBase] | None = None,
    trust_scores_map: dict[str, TrustScores] | None = None,
) -> str:
    kbs = kbs or {}
    trust_scores_map = trust_scores_map or {}
    parts = []

    for name, transcripts in talkers_data.items():
        short, mid, _long_list = split_by_time_window(transcripts)
        trust = trust_scores_map.get(name)
        kb = kbs.get(name)

        parts.append(f"# 博主：{name}")

        if trust:
            best = max(
                ("短期", trust.short_term),
                ("中期", trust.mid_term),
                ("长期", trust.long_term),
                key=lambda x: x[1],
            )
            parts.append(
                f"信任评估：短期 {trust.short_term} / 中期 {trust.mid_term} / 长期 {trust.long_term} "
                f"（{best[0]}判断力最强，{best[1]} 分）\n"
            )

        # KB summary for this talker
        if kb and kb.nodes:
            parts.append("### 历史知识库")
            for node_name, node in kb.nodes.items():
                parts.append(
                    f"- {node_name}：{node.core_claim}"
                    f"（趋势: {node.trend}, 置信度: {node.confidence}）"
                )
            parts.append("")

        # Short-term full text
        source = short if short else mid if mid else transcripts
        label = "### 最新文案（决策核心）" if short else "### 近期文案"
        parts.append(label)
        for t in source:
            parts.append(f"## {t.date}")
            for entry in t.entries:
                parts.append(f"### {entry.title}")
                parts.append(entry.content)
                parts.append("")

    return "\n".join(parts)
