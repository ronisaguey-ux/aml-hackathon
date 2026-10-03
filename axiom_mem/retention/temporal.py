import re
from datetime import datetime, timezone
from typing import List, Dict, Any, Tuple
from axiom_mem import config

TEMPORAL_UPDATE_PATTERNS = [
    re.compile(r'\b(moved to|relocated to|now living in|lives in|living in)\b', re.IGNORECASE),
    re.compile(r'\b(changed to|updated to|switched to|replaced with|now using|now set to)\b', re.IGNORECASE),
    re.compile(r'\b(reverted|superseded|overridden|fixed by|migrated to)\b', re.IGNORECASE),
    re.compile(r'\b(now|currently|at present|as of today|as of now|recently)\b', re.IGNORECASE),
]


def format_iso_timestamp(timestamp_ms: Any, epoch_fallback: float) -> str:
    """Format timestamp into standard ISO-8601 UTC string (e.g. 2026-07-01T12:00:00Z)."""
    try:
        if timestamp_ms is not None and int(timestamp_ms) > 0:
            dt = datetime.fromtimestamp(int(timestamp_ms) / 1000.0, tz=timezone.utc)
            return dt.strftime("%Y-%m-%dT%H:%M:%SZ")
    except Exception:
        pass
    dt = datetime.fromtimestamp(epoch_fallback, tz=timezone.utc)
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


class TemporalResolver:
    """
    Temporal Resolution Engine:
    Resolves conflicting/updating facts across session timelines.
    Ranks the latest valid version first while preserving superseded context lower down.
    """
    def __init__(self, recency_boost: float = config.TEMPORAL_RECENCY_BOOST):
        self.recency_boost = recency_boost

    def apply_temporal_ranking(
        self,
        candidates: List[Tuple[Dict[str, Any], float]],
        query: str
    ) -> List[Tuple[Dict[str, Any], float]]:
        if not candidates:
            return []

        # Check if query asks about current state or temporal progression
        is_temporal_query = bool(re.search(
            r'\b(when|latest|current|currently|now|recent|recently|last|history|before|after|changed|update)\b',
            query,
            re.IGNORECASE
        ))

        # Find maximum timestamp among candidates to normalize recency
        valid_timestamps = [
            m.get("timestamp_ms") or (m.get("created_at_epoch", 0) * 1000)
            for m, _ in candidates
        ]
        max_ts = max(valid_timestamps) if valid_timestamps else 1.0
        min_ts = min(valid_timestamps) if valid_timestamps else 0.0
        ts_span = max(max_ts - min_ts, 1.0)

        adjusted: List[Tuple[Dict[str, Any], float]] = []
        for mem, score in candidates:
            content = mem.get("content", "")
            mem_ts = mem.get("timestamp_ms") or (mem.get("created_at_epoch", 0) * 1000)
            
            # Normalized recency factor [0.0 to 1.0]
            recency_ratio = (mem_ts - min_ts) / ts_span

            # Detect if message contains update language
            has_update_marker = any(p.search(content) for p in TEMPORAL_UPDATE_PATTERNS)

            multiplier = 1.0
            if has_update_marker:
                # If it's an update, recency matters even more
                multiplier += (self.recency_boost - 1.0) * recency_ratio
            elif is_temporal_query:
                # For temporal queries, give modest boost to recent evidence
                multiplier += (self.recency_boost - 1.0) * 0.5 * recency_ratio

            adjusted.append((mem, score * multiplier))

        # Sort descending by adjusted score
        adjusted.sort(key=lambda x: x[1], reverse=True)
        return adjusted
