"""Per-transcript digest — AI cleans colloquial filler, extracts key points."""
import json
from datetime import date
from pathlib import Path

from financy_talk.config import DATA_DIR, get_api_key, get_model_config, DEEPSEEK_BASE_URL
from financy_talk.data.loader import load_talker_transcripts

DIGEST_PROMPT = """你是一位信息提炼专家。请阅读以下财经博主的视频文案，完成以下任务：

1. 去除所有口语化措辞（如"家人们""懂的都懂""这个那个"等），保留实质内容
2. 提取每条行业观点/判断，归纳为简洁的信息点（每条不超过100字）
3. 合并重复/相似的观点
4. 保留原文中的关键数据、日期、公司名称、产品型号

输出格式：纯文本，用 ## 标题 + 要点列表（- 开头）组织。不要输出任何JSON或代码块。"""


def _digest_dir(name: str) -> Path:
    return DATA_DIR / name / "digest"


def _transcribed_ids_path(name: str) -> Path:
    return DATA_DIR / name / ".digested.json"


def _load_digested_ids(name: str) -> set[str]:
    path = _transcribed_ids_path(name)
    if not path.exists():
        return set()
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return set(data.get("dates", []))
    except Exception:
        return set()


def _save_digested_ids(name: str, new_dates: set[str]) -> None:
    path = _transcribed_ids_path(name)
    existing = _load_digested_ids(name)
    merged = existing | new_dates
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(
            {"dates": sorted(merged), "updated": date.today().isoformat()},
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )


def digest_transcripts(
    name: str,
    *,
    force: bool = False,
    client: "OpenAI | None" = None,
) -> int:
    """Run per-transcript AI cleaning for all undigested files.

    Returns the number of transcripts processed.
    """
    transcripts = load_talker_transcripts(name)
    digested_dates = _load_digested_ids(name) if not force else set()
    pending = [t for t in transcripts if t.date not in digested_dates]

    if not pending:
        return 0

    if client is None:
        from openai import OpenAI
        model_config = get_model_config("haiku")  # cheap model for per-file cleaning
        client = OpenAI(api_key=get_api_key(), base_url=DEEPSEEK_BASE_URL, timeout=120)
    else:
        model_config = get_model_config("haiku")

    out_dir = _digest_dir(name)
    out_dir.mkdir(parents=True, exist_ok=True)
    processed = 0

    for t in pending:
        text = _transcript_to_text(t)
        try:
            response = client.chat.completions.create(
                model=model_config.model,
                messages=[
                    {"role": "system", "content": DIGEST_PROMPT},
                    {"role": "user", "content": text},
                ],
                temperature=0.2,
                max_tokens=model_config.max_tokens,
                timeout=120,
            )
            content = response.choices[0].message.content
            if content:
                out_path = out_dir / f"{t.date}.txt"
                out_path.write_text(content.strip(), encoding="utf-8")
                processed += 1
        except Exception:
            continue

    if processed:
        _save_digested_ids(name, {t.date for t in pending if (out_dir / f"{t.date}.txt").exists()})

    return processed


def load_digests(name: str) -> dict[str, str]:
    """Load all digest files, returning {date: content} mapping."""
    d_dir = _digest_dir(name)
    if not d_dir.exists():
        return {}
    result = {}
    for f in sorted(d_dir.glob("*.txt")):
        date_str = f.stem
        result[date_str] = f.read_text(encoding="utf-8")
    return result


def _transcript_to_text(t: "TalkerTranscript") -> str:
    parts = [f"# {t.date}"]
    for entry in t.entries:
        parts.append(f"## {entry.title}")
        parts.append(entry.content)
        parts.append("")
    return "\n".join(parts)
