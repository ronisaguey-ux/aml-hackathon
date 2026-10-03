import re
from datetime import datetime, timezone
from typing import List, Dict, Any, Tuple
from axiom_mem import config

STATE_CHANGE_PATTERNS = [
    re.compile(r'\b(moved to|relocated to|now living in|lives in|living in)\b', re.IGNORECASE),
    re.compile(r'\b(changed to|updated to|switched to|replaced with|now using|now set to|now is)\b', re.IGNORECASE),
    re.compile(r'\b(upgraded to|migrated to|renamed to|corrected|correction:?|fixed by)\b', re.IGNORECASE),
    re.compile(r'\b(reverted|superseded|overridden|deprecated|no longer using|no longer)\b', re.IGNORECASE),
    re.compile(r'\b(previously|instead of|actually|sorry|as of now|at present|these days)\b', re.IGNORECASE),
    re.compile(r'\b(now|currently|latest|recently)\b', re.IGNORECASE),
]

PAST_TENSE_QUERY_PATTERN = re.compile(
    r'\b(originally|before|previously|initially|used to|former|formerly|prior|earlier|first lived|started as|old database|what was (the |my )?(original|old|previous|initial|former|earlier)|where was (the |my )?(original|old|previous|initial|former|earlier))\b',
    re.IGNORECASE
)

PRESENT_TENSE_QUERY_PATTERN = re.compile(
    r'\b(now|currently|these days|latest|present|at present|active|newest|today|current|is my role now|where do i currently|current active)\b',
    re.IGNORECASE
)

GENERAL_TEMPORAL_QUERY_PATTERN = re.compile(
    r'\b(when|latest|current|currently|now|recent|recently|last|history|before|after|changed|update|migrat|relocat)\b',
    re.IGNORECASE
)


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
    Precision Temporal Resolution Engine (Column C):
    - Tense-aware routing:
        * Past-tense queries prioritize the historical/original state.
        * Present-tense queries prioritize the latest valid updated state.
    - Constrained boosting:
        * Only applies temporal adjustments between competing relevant candidates.
        * NEVER promotes unrelated background distractors based on timestamp alone.
    - Preserves full temporal trajectory in output.
    """
    def __init__(self, recency_boost: float = config.TEMPORAL_RECENCY_BOOST):
        self.recency_boost = max(recency_boost, 1.60)

    def apply_temporal_ranking(
        self,
        candidates: List[Tuple[Dict[str, Any], float]],
        query: str
    ) -> List[Tuple[Dict[str, Any], float]]:
        if not candidates or len(candidates) < 2:
            return candidates

        is_past_query = bool(PAST_TENSE_QUERY_PATTERN.search(query))
        is_present_query = bool(PRESENT_TENSE_QUERY_PATTERN.search(query))
        is_general_temporal = bool(GENERAL_TEMPORAL_QUERY_PATTERN.search(query))

        # Check if any candidate has state change markers
        has_any_update = any(
            any(p.search(m.get("content", "")) for p in STATE_CHANGE_PATTERNS)
            for m, _ in candidates[:10]
        )
        if not (is_past_query or is_present_query or is_general_temporal or has_any_update):
            return candidates

        # Determine relevance threshold (only compete within top 25% of top hybrid score)
        top_score = candidates[0][1]
        score_threshold = top_score * 0.75

        # Extract timestamps strictly among relevant candidates or update memories
        relevant_candidates = [
            (m, s) for m, s in candidates
            if s >= score_threshold or any(p.search(m.get("content", "")) for p in STATE_CHANGE_PATTERNS)
        ]
        if not relevant_candidates:
            return candidates

        timestamps = [
            m.get("timestamp_ms") or int(m.get("created_at_epoch", 0) * 1000)
            for m, _ in relevant_candidates
        ]
        max_ts = max(timestamps) if timestamps else 1.0
        min_ts = min(timestamps) if timestamps else 0.0
        ts_span = max(max_ts - min_ts, 1.0)

        adjusted: List[Tuple[Dict[str, Any], float]] = []
        for mem, score in candidates:
            has_update_marker = any(p.search(mem.get("content", "")) for p in STATE_CHANGE_PATTERNS)

            # Never boost background memories that have neither high initial score nor an update marker
            if score < score_threshold and not has_update_marker:
                adjusted.append((mem, score))
                continue

            mem_ts = mem.get("timestamp_ms") or int(mem.get("created_at_epoch", 0) * 1000)
            recency_ratio = (mem_ts - min_ts) / ts_span

            multiplier = 1.0

            if is_past_query:
                # Query specifically asks for previous/original state
                if not has_update_marker and recency_ratio <= 0.4:
                    # Early historical baseline state gets top multiplier
                    multiplier = self.recency_boost * 1.5
                elif has_update_marker or recency_ratio > 0.6:
                    # Subsequent or superseded state is discounted below baseline
                    multiplier = 0.65
                else:
                    multiplier = 1.0 + (1.0 - recency_ratio) * 0.2

            else:
                # Query asks for current/latest state or a state update occurred
                if has_update_marker and recency_ratio >= 0.5:
                    # Latest valid update gets decisive multiplier
                    multiplier = self.recency_boost * 2.0
                elif recency_ratio >= 0.7:
                    multiplier = self.recency_boost * 1.3
                elif is_present_query and recency_ratio < 0.5:
                    # Superseded earlier state is discounted when querying for current state
                    multiplier = 0.70
                elif recency_ratio < 0.4:
                    multiplier = 0.85
                else:
                    multiplier = 1.0

            adjusted.append((mem, score * multiplier))

        # Stable tiebreak: sort by score descending, then timestamp descending, then id
        adjusted.sort(
            key=lambda x: (
                round(x[1], 6),
                x[0].get("timestamp_ms") or int(x[0].get("created_at_epoch", 0) * 1000),
                x[0].get("id", "")
            ),
            reverse=True
        )
        return adjusted
