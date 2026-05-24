"""Multi-talker comparison and aggregation via OpenAI API."""

from financy_talk.data.loader import TalkerTranscript
from financy_talk.config import get_model_config, get_api_key, DEEPSEEK_BASE_URL

COMPARISON_PROMPT = """你是一位资深财经分析师。以下是多位财经博主的近期观点汇总，请完成以下分析：

1. **各博主核心观点对比**：逐位总结核心观点
2. **异同分析**：找出观点的一致性与分歧
3. **产业趋势共识**：提炼多位博主共同关注的产业方向
4. **股市综合研判**：结合多方观点，对当前A股/港股给出综合研判建议

请用中文输出。格式简洁清晰。"""


def aggregate_talkers(
    talkers_data: dict[str, list[TalkerTranscript]],
    client: "OpenAI | None" = None,
) -> str:
    model_config = get_model_config("opus")

    if client is None:
        from openai import OpenAI
        client = OpenAI(api_key=get_api_key(), base_url=DEEPSEEK_BASE_URL, timeout=120)

    user_content = _build_comparison_prompt(talkers_data)

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


def _build_comparison_prompt(talkers_data: dict[str, list[TalkerTranscript]]) -> str:
    parts = []
    for name, transcripts in talkers_data.items():
        parts.append(f"# 博主：{name}")
        for t in transcripts:
            parts.append(f"## {t.date}")
            for entry in t.entries:
                parts.append(f"### {entry.title}")
                parts.append(entry.content)
                parts.append("")
    return "\n".join(parts)
