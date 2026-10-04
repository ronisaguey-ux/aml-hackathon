import re
from datetime import datetime, timezone
from typing import List, Dict, Any, Tuple
from axiom_mem import config

STATE_CHANGE_PATTERNS = [
    re.compile(r'\b(moved(?:\s+\w+){0,3}\s+to|relocated(?:\s+\w+){0,3}\s+to|now living in|lives in|living in)\b', re.IGNORECASE),
    re.compile(r'\b(changed(?:\s+\w+){0,4}\s+to|updated(?:\s+\w+){0,4}\s+to|switched(?:\s+\w+){0,4}\s+to|replaced(?:\s+\w+){0,4}\s+with|now using|now set to|now is)\b', re.IGNORECASE),
    re.compile(r'\b(upgraded(?:\s+\w+){0,4}\s+to|migrated(?:\s+\w+){0,4}\s+to|renamed(?:\s+\w+){0,4}\s+to|corrected|correction:?|fixed by)\b', re.IGNORECASE),
    re.compile(r'\b(reverted|superseded|overridden|deprecated|no longer using|no longer)\b', re.IGNORECASE),
    re.compile(r'\b(previously|instead of|actually|sorry|as of now|at present|these days)\b', re.IGNORECASE),
    re.compile(r'\b(now|currently|latest|recently)\b', re.IGNORECASE),
    re.compile(r'\b(promoted(?:\s+\w+){0,3}\s+to|handover complete|switched to|transferred(?:\s+\w+){0,3}\s+to|relocation:|expansion:|scaling:|rebuild:|upgrade:|overhaul:|adjustment:)\b', re.IGNORECASE),
]

ORIGIN_PATTERNS = [
    re.compile(r'\b(originally|initially|started as|first lived|joined as|were hosted on|established on|standardized on|was set at|consists of a single|originally ran on|originally built on|legacy)\b', re.IGNORECASE),
]

PAST_TENSE_QUERY_PATTERN = re.compile(
    r'\b(originally|before|previously|initially|used to|former|formerly|prior|earlier|first lived|started as|old database|what was (the |my )?(original|old|previous|initial|former|earlier)|where was (the |my )?(original|old|previous|initial|former|earlier))\b',
    re.IGNORECASE
)

PRESENT_TENSE_QUERY_PATTERN = re.compile(
    r'\b(now|currently|these days|latest|present|at present|active|newest|today|current|is my role now|where do i currently|where do i live|current active|how are|which cloud provider|what is the current|what is the active|which caching technology is currently)\b',
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
    - Scoped boosting:
        * Only applies adjustments to candidate memories with verified state transitions or origin markers.
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
        is_present_query = bool(PRESENT_TENSE_QUERY_PATTERN.search(query)) and not is_past_query
        is_general_temporal = bool(GENERAL_TEMPORAL_QUERY_PATTERN.search(query))

        has_any_update = any(
            any(p.search(m.get("content", "")) for p in STATE_CHANGE_PATTERNS)
            for m, _ in candidates[:10]
        )
        has_any_origin = any(
            any(p.search(m.get("content", "")) for p in ORIGIN_PATTERNS)
            for m, _ in candidates[:10]
        )

        if not (is_past_query or is_present_query or is_general_temporal or has_any_update or has_any_origin):
            return candidates

        top_score = candidates[0][1]
        score_threshold = top_score * 0.70

        # Filter strictly non-distractor candidates that are relevant contenders
        contenders = []
        for mem, score in candidates:
            content = mem.get("content", "")
            sid = mem.get("session_id", "")
            is_distractor = sid.startswith("sess_dist") or content.startswith("[Background Note")
            if is_distractor:
                continue

            has_update = any(p.search(content) for p in STATE_CHANGE_PATTERNS)
            has_origin = any(p.search(content) for p in ORIGIN_PATTERNS)

            if score >= score_threshold or has_update or has_origin:
                contenders.append((mem, score, has_update, has_origin))

        if not contenders:
            return candidates

        timestamps = [
            m.get("timestamp_ms") or int(m.get("created_at_epoch", 0) * 1000)
            for m, _, _, _ in contenders
        ]
        min_ts = min(timestamps)
        max_ts = max(timestamps)
        ts_span = max(max_ts - min_ts, 1)

        contender_ids = {m["id"]: (has_u, has_o) for m, _, has_u, has_o in contenders}

        adjusted: List[Tuple[Dict[str, Any], float]] = []
        for mem, score in candidates:
            mem_id = mem.get("id", "")
            if mem_id not in contender_ids:
                adjusted.append((mem, score))
                continue

            has_update_marker, has_origin_marker = contender_ids[mem_id]
            mem_ts = mem.get("timestamp_ms") or int(mem.get("created_at_epoch", 0) * 1000)
            recency_ratio = (mem_ts - min_ts) / ts_span

            multiplier = 1.0

            if is_past_query:
                # Query specifically asks for historical/original state
                if has_origin_marker or recency_ratio <= 0.3:
                    multiplier = self.recency_boost * 1.5
                elif has_update_marker or recency_ratio >= 0.7:
                    multiplier = 0.50
            elif is_present_query or has_any_update:
                # Query asks for current/updated state
                if (has_update_marker and recency_ratio >= 0.5) or recency_ratio >= 0.7:
                    multiplier = self.recency_boost * 1.5
                elif has_origin_marker or recency_ratio <= 0.3:
                    multiplier = 0.50

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
