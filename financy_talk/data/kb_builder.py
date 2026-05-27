"""Knowledge base builder — AI-powered extraction and merge."""
import json
from datetime import date, timedelta
from pathlib import Path

from financy_talk.config import DATA_DIR, get_api_key, get_model_config, DEEPSEEK_BASE_URL
from financy_talk.data.loader import load_talker_transcripts, TalkerTranscript
from financy_talk.data.digest import load_digests
from financy_talk.data.kb_schema import KnowledgeBase, KBNode, Evidence

EXTRACTION_PROMPT = """你是一位信息提取专家。请阅读以下财经博主的视频文案，提取其中对具体行业的观点和判断。

对于每个提到的行业/细分赛道，提取以下信息：
- core_claim: 核心判断（一句话，去口语化）
- confidence: high / medium / low
- trend: accelerating / steady / decelerating / turning
- new_evidence: 论据列表 [{"date": "...", "point": "..."}]

严格按以下JSON结构输出（最外层必须是 "nodes" 键）：

{
  "nodes": {
    "行业名称": {
      "core_claim": "...",
      "confidence": "high",
      "trend": "accelerating",
      "new_evidence": []
    }
  }
}

只提取有实质行业判断的内容，跳过数据播报和口语感慨。输出纯JSON，不要markdown代码块标记。确保JSON完整闭合。"""


def _kb_path(name: str) -> Path:
    return DATA_DIR / name / "kb.json"


def load_kb(name: str) -> KnowledgeBase | None:
    """Load existing knowledge base, or None if it doesn't exist."""
    path = _kb_path(name)
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        nodes = {}
        for node_name, node_data in data.get("nodes", {}).items():
            evidence = [Evidence(**e) for e in node_data.pop("evidence", [])]
            nodes[node_name] = KBNode(**node_data, evidence=evidence)
        return KnowledgeBase(updated=data.get("updated", ""), nodes=nodes)
    except Exception:
        return None


def save_kb(name: str, kb: KnowledgeBase) -> Path:
    """Persist knowledge base to kb.json."""
    path = _kb_path(name)
    path.parent.mkdir(parents=True, exist_ok=True)
    data = {
        "updated": kb.updated,
        "nodes": {
            node_name: {
                "core_claim": node.core_claim,
                "confidence": node.confidence,
                "trend": node.trend,
                "evidence": [{"date": e.date, "point": e.point} for e in node.evidence],
            }
            for node_name, node in kb.nodes.items()
        },
    }
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def _filter_recent(transcripts: list[TalkerTranscript], days: int) -> list[TalkerTranscript]:
    cutoff = (date.today() - timedelta(days=days)).isoformat()
    return [t for t in transcripts if t.date >= cutoff]


def _build_extraction_prompt(
    transcripts: list[TalkerTranscript],
    existing_node_names: list[str] | None = None,
    digests: dict[str, str] | None = None,
) -> str:
    digests = digests or {}
    parts = []
    for t in transcripts:
        parts.append(f"## {t.date}")
        if t.date in digests:
            # Use cleaned digest instead of raw transcript
            parts.append(digests[t.date])
        else:
            for entry in t.entries:
                parts.append(f"### {entry.title}")
                content = entry.content
                if len(content) > 500:
                    content = content[:500] + "..."
                parts.append(content)
        parts.append("")
    body = "\n".join(parts)

    if existing_node_names:
        names = "\n".join(f"  - {n}" for n in existing_node_names)
        return (
            f"注意：知识库中已存在以下行业节点，请务必使用**完全相同的名称**"
            f"来归类新增论据，不要创建新的或相似的节点名：\n{names}\n\n{body}"
        )

    return body


def _parse_extraction_result(raw: str) -> dict[str, KBNode]:
    """Parse AI extraction result into KBNode dict. Handles both formats:

    {"nodes": {"CCL": {...}}}   — expected
    {"CCL": {...}}              — also accepted (no wrapper)
    """
    text = raw.strip()
    if text.startswith("```"):
        lines = text.split("\n")
        text = "\n".join(lines[1:-1] if lines[-1].startswith("```") else lines[1:])
    data = json.loads(text)

    # Accept both wrapped and unwrapped formats
    if "nodes" in data and isinstance(data["nodes"], dict):
        source = data["nodes"]
    else:
        # Treat every top-level key that looks like a node entry as a node
        source = {
            k: v for k, v in data.items()
            if isinstance(v, dict) and "core_claim" in v
        }

    nodes: dict[str, KBNode] = {}
    for node_name, node_data in source.items():
        evidence_data = node_data.pop("new_evidence", []) or node_data.pop("evidence", [])
        evidence = [Evidence(**e) for e in evidence_data]
        nodes[node_name] = KBNode(**node_data, evidence=evidence)
    return nodes


def build_kb(
    name: str,
    *,
    rebuild_all: bool = False,
    client: "OpenAI | None" = None,
) -> KnowledgeBase:
    """Extract industry knowledge from recent transcripts and merge into KB.

    Args:
        name: Talker name.
        rebuild_all: If True, process all transcripts (initial build).
                     Otherwise only process last 5 days.
        client: Optional pre-configured OpenAI client.
    """
    transcripts = load_talker_transcripts(name)

    if rebuild_all:
        source_transcripts = transcripts
    else:
        source_transcripts = _filter_recent(transcripts, 5)

    if not source_transcripts:
        # Nothing new to extract — return existing KB or empty one
        return load_kb(name) or KnowledgeBase(updated=date.today().isoformat())

    if client is None:
        from openai import OpenAI
        model_config = get_model_config("opus")  # need more output tokens for KB JSON
        client = OpenAI(api_key=get_api_key(), base_url=DEEPSEEK_BASE_URL, timeout=120)
    else:
        model_config = get_model_config("opus")

    existing_kb = load_kb(name)
    existing_names = list(existing_kb.nodes.keys()) if existing_kb else None
    digests = load_digests(name)
    user_content = _build_extraction_prompt(
        source_transcripts, existing_names, digests=digests,
    )

    response = client.chat.completions.create(
        model=model_config.model,
        messages=[
            {"role": "system", "content": EXTRACTION_PROMPT},
            {"role": "user", "content": user_content},
        ],
        temperature=0.3,
        max_tokens=model_config.max_tokens,
        timeout=120,
    )
    content = response.choices[0].message.content
    if content is None:
        raise RuntimeError("KB extraction API returned None")
    content = content.strip()
    if not content:
        finish = response.choices[0].finish_reason
        raise RuntimeError(
            f"KB extraction returned empty content (finish_reason={finish})."
        )

    new_nodes = _parse_extraction_result(content)

    # Merge with existing KB (loaded above for node name hint)
    kb = existing_kb or KnowledgeBase(updated=date.today().isoformat())

    for node_name, new_node in new_nodes.items():
        if node_name in kb.nodes:
            old = kb.nodes[node_name]
            if new_node.core_claim.strip() != old.core_claim.strip():
                old.core_claim = new_node.core_claim
            old.confidence = new_node.confidence
            old.trend = new_node.trend
            for ev in new_node.evidence:
                if not any(e.date == ev.date and e.point == ev.point for e in old.evidence):
                    old.evidence.append(ev)
        else:
            kb.nodes[node_name] = new_node

    # Archive evidence older than 6 months
    cutoff = date.today() - timedelta(days=KnowledgeBase.LONG_TERM_DAYS)
    kb.archive_stale_evidence(cutoff)
    kb.updated = date.today().isoformat()

    save_kb(name, kb)
    return kb
