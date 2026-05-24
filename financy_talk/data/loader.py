"""Load and parse talker transcript markdown files."""
from dataclasses import dataclass, field
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
