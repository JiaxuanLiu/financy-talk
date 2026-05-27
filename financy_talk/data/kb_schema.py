"""Knowledge base data structures for talker industry analysis."""
from dataclasses import dataclass, field
from datetime import date


@dataclass
class Evidence:
    date: str
    point: str


@dataclass
class KBNode:
    core_claim: str
    confidence: str  # high / medium / low
    trend: str       # accelerating / steady / decelerating / turning
    evidence: list[Evidence] = field(default_factory=list)


@dataclass
class KnowledgeBase:
    updated: str
    nodes: dict[str, KBNode] = field(default_factory=dict)

    LONG_TERM_DAYS: int = 180

    def archive_stale_evidence(self, cutoff: date | None = None) -> None:
        """Remove evidence older than 180 days, keeping at least 3 per node.

        The "at least 3" fallback only triggers when there are more than
        3 evidence items total — it prevents wiping out a large evidence
        set.  Nodes with ≤ 3 items simply drop the stale ones.
        """
        if cutoff is None:
            cutoff = date.today()
        threshold = cutoff.isoformat()
        for node in self.nodes.values():
            kept = [e for e in node.evidence if e.date >= threshold]
            if len(node.evidence) > 3 and len(kept) < 3:
                kept = sorted(node.evidence, key=lambda e: e.date, reverse=True)[:3]
            node.evidence = kept
