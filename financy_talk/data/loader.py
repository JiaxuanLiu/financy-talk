"""Load and parse talker transcript markdown files."""
import re
from dataclasses import dataclass, field
from datetime import date, timedelta
from pathlib import Path

from financy_talk.config import DATA_DIR


@dataclass
class TranscriptEntry:
    title: str
    content: str


@dataclass
class TalkerTranscript:
    date: str
    entries: list[TranscriptEntry] = field(default_factory=list)


def load_talker_transcripts(name: str, talkers_root: Path | None = None) -> list[TalkerTranscript]:
    if ".." in name or "/" in name or "\\" in name:
        raise ValueError(f"Invalid talker name: {name}")
    root = talkers_root or DATA_DIR
    talker_dir = root / name
    if not talker_dir.is_dir():
        raise FileNotFoundError(f"Talker '{name}' not found at {talker_dir}")

    md_files = sorted(talker_dir.glob("*.md"))
    if not md_files:
        raise FileNotFoundError(f"No markdown files found for talker '{name}' at {talker_dir}")

    transcripts: list[TalkerTranscript] = []
    for md_file in md_files:
        transcript = _parse_markdown(md_file.read_text(encoding="utf-8"))
        transcripts.append(transcript)
    return transcripts


def list_talkers(talkers_root: Path | None = None) -> list[str]:
    root = talkers_root or DATA_DIR
    if not root.is_dir():
        return []
    return sorted(
        d.name for d in root.iterdir()
        if d.is_dir()
    )


def _parse_markdown(text: str) -> TalkerTranscript:
    """Parse markdown: # Date, ## Title, then content."""
    lines = text.strip().split("\n")
    date: str | None = None
    entries: list[TranscriptEntry] = []
    current_title: str | None = None
    current_lines: list[str] = []

    for line in lines:
        if line.startswith("# ") and not line.startswith("## "):
            if date is None:
                date = line[2:].strip()
            continue
        if line.startswith("## "):
            if current_title is not None:
                entries.append(TranscriptEntry(
                    title=current_title,
                    content="\n".join(current_lines).strip(),
                ))
            current_title = line[3:].strip()
            current_lines = []
            continue
        if current_title is not None:
            current_lines.append(line)

    if current_title is not None:
        entries.append(TranscriptEntry(
            title=current_title,
            content="\n".join(current_lines).strip(),
        ))

    return TalkerTranscript(date=date or "", entries=entries)


# ---------------------------------------------------------------------------
# Trust scores & time windows
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class TrustScores:
    short_term: int   # 0-100
    mid_term: int
    long_term: int

    SHORT_DAYS: int = 5
    MID_DAYS: int = 20
    LONG_DAYS: int = 180


def parse_trust_scores(name: str) -> TrustScores | None:
    """Extract trust scores from a talker's README.md. Returns None if unparseable."""
    readme = DATA_DIR / name / "README.md"
    if not readme.exists():
        return None
    text = readme.read_text(encoding="utf-8")

    def _extract(label: str) -> int | None:
        m = re.search(rf"{label}.*?(\d+)\s*分", text)
        return int(m.group(1)) if m else None

    short_val = _extract("短期信任评分")
    mid_val = _extract("中期信任评分")
    long_val = _extract("长期信任评分")

    if short_val is None or mid_val is None or long_val is None:
        return None
    return TrustScores(short_term=short_val, mid_term=mid_val, long_term=long_val)


def split_by_time_window(
    transcripts: list[TalkerTranscript],
) -> tuple[list[TalkerTranscript], list[TalkerTranscript], list[TalkerTranscript]]:
    """Split transcripts into (short, mid, long) windows based on TrustScores day ranges.

    short: 0-5 days,  mid: 5-20 days,  long: 20-180 days.
    Transcripts older than 180 days are dropped.
    """
    today = date.today()
    short = []
    mid = []
    long_list = []

    for t in transcripts:
        try:
            d = date.fromisoformat(t.date)
        except (ValueError, TypeError):
            continue
        delta = (today - d).days
        if delta < TrustScores.SHORT_DAYS:
            short.append(t)
        elif delta < TrustScores.MID_DAYS:
            mid.append(t)
        elif delta < TrustScores.LONG_DAYS:
            long_list.append(t)
        # else: older than 180 days — drop

    return short, mid, long_list
