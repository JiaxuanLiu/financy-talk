"""Single-talker analysis via OpenAI API."""

from openai import APIError

from financy_talk.data.loader import TalkerTranscript

SYSTEM_PROMPT = """你是一位资深财经分析师。请根据以下抖音财经博主近期的视频文案，完成以下分析：

1. **核心观点总结**：提炼该博主近期表达的核心观点
2. **产业趋势分析**：根据其观点，汇总对应的产业趋势
3. **股市研判**：基于以上分析，对当前A股/港股相关板块做出研判建议

请用中文输出。格式简洁清晰。"""


def analyze_talker(
    name: str,
    transcripts: list[TalkerTranscript],
    client: "OpenAI | None" = None,
) -> str:
    if client is None:
        from openai import OpenAI
        from financy_talk.config import get_api_key
        client = OpenAI(api_key=get_api_key(), timeout=120)

    user_content = _build_user_prompt(name, transcripts)

    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_content},
            ],
            temperature=0.7,
            max_tokens=4000,
            timeout=120,
        )
    except APIError as e:
        raise
    return response.choices[0].message.content


def _build_user_prompt(name: str, transcripts: list[TalkerTranscript]) -> str:
    parts = [f"博主：{name}\n"]
    for t in transcripts:
        parts.append(f"## {t.date}")
        for entry in t.entries:
            parts.append(f"### {entry.title}")
            parts.append(entry.content)
            parts.append("")
    return "\n".join(parts)
