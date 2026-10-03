import re
from typing import List, Dict, Any, Tuple
from axiom_mem import config
from axiom_mem.store.db import SQLiteStore

CODE_INDICATORS = [
    re.compile(r'```', re.MULTILINE),
    re.compile(r'\b(def |class |function |import |from |return |const |let |var |fn |pub |impl )\b'),
    re.compile(r'\b(pip |npm |cargo |curl |docker |git |kubectl |pytest |python |bash |mvn |gradle |systemctl |vault-cli |db-verify )\b'),
    re.compile(r'(\bTraceback\b|\bException\b|\bError:|\bFailed:\b|\bexit code \d+|\bRoot Cause:|\bRepair Action:|\bDiagnostic Trace:|\bSIGKILL\b|\bOOM\b)'),
    re.compile(r'\b(--[a-zA-Z0-9_\-]+|\-[a-zA-Z0-9]+)\b'),
    re.compile(r'(`[^`]+`)'),
]

PROCEDURAL_INDICATORS = [
    re.compile(r'(^\s*\d+[\.\)]\s+|^\s*[-*]\s+)', re.MULTILINE),
    re.compile(r'\b(step \d+:?|first|second|third|fourth|then|finally|after that|next step|prerequisite)\b', re.IGNORECASE),
    re.compile(r'\b(must always|must never|never|required to|procedure|rule:|policy:|guideline:|instruction:)\b', re.IGNORECASE),
]

# Strict operational intent patterns (excludes generic informational questions)
EXECUTION_QUERY_PATTERNS = [
    re.compile(r'\b(how (do i|to|can i|should i)|steps? (to|for)|procedure (to|for)|instructions? (to|for)|workflow (to|for)|run the|execute the|deploy the|install the)\b', re.IGNORECASE),
    re.compile(r'\b(how to fix|how to repair|debug the|how to resolve|fix the|repair the|resolve the|repair action)\b', re.IGNORECASE),
    re.compile(r'\b(step by step)\b', re.IGNORECASE),
]

REPAIR_QUERY_PATTERN = re.compile(r'\b(repair|fix|resolve|solution|action to take)\b', re.IGNORECASE)
REPAIR_ACTION_PATTERN = re.compile(r'\b(repair action|fix:|solution:|resolution:|action:)\b', re.IGNORECASE)


def is_procedural_content(text: str) -> bool:
    """Classify if memory content contains procedural steps, code, rules, or tracebacks."""
    for p in CODE_INDICATORS:
        if p.search(text):
            return True
    for p in PROCEDURAL_INDICATORS:
        if p.search(text):
            return True
    return False


class ExecutionRetainer:
    """
    Column G ("Context Learning & Execution") Engine:
    - Recognizes operational execution queries.
    - Gates procedural expansion strictly to high-relevance sessions (prevents distractor promotion).
    - When repair/fix is queried, prioritizes the direct solution/action at Rank 1.
    - Returns the entire ordered procedure block contiguously before non-procedural results.
    """
    def __init__(self, store: SQLiteStore, execution_boost: float = config.EXECUTION_BOOST):
        self.store = store
        self.execution_boost = max(execution_boost, 1.50)

    def apply_execution_enhancements(
        self,
        user_id: str,
        candidates: List[Tuple[Dict[str, Any], float]],
        query: str,
        top_k: int = 100
    ) -> List[Tuple[Dict[str, Any], float]]:
        if not candidates:
            return []

        is_execution_query = any(p.search(query) for p in EXECUTION_QUERY_PATTERNS)

        if not is_execution_query:
            # For non-execution queries, apply gentle procedural boost without reordering blocks
            boosted: List[Tuple[Dict[str, Any], float]] = []
            for mem, score in candidates:
                is_proc = mem.get("is_procedural", 0) or is_procedural_content(mem.get("content", ""))
                multiplier = 1.0 + (self.execution_boost - 1.0) * 0.2 if is_proc else 1.0
                boosted.append((mem, score * multiplier))
            boosted.sort(
                key=lambda x: (
                    round(x[1], 6),
                    x[0].get("timestamp_ms") or int(x[0].get("created_at_epoch", 0) * 1000),
                    x[0].get("id", "")
                ),
                reverse=True
            )
            return boosted

        # Operational Execution Query Flow:
        top_score = candidates[0][1]
        relevance_threshold = top_score * 0.80

        # Only consider procedural sessions from top-tier matching candidates
        procedural_sessions = set()
        cand_scores: Dict[str, float] = {}

        for mem, score in candidates[:10]:
            cand_scores[mem["id"]] = score
            if score >= relevance_threshold:
                is_proc = mem.get("is_procedural", 0) or is_procedural_content(mem.get("content", ""))
                if is_proc:
                    sess_id = mem.get("session_id")
                    if sess_id:
                        procedural_sessions.add(sess_id)

        if not procedural_sessions:
            return candidates

        # Fetch procedure blocks for the matched sessions
        procedure_memories: List[Dict[str, Any]] = []
        seen_proc_ids = set()

        for sess_id in procedural_sessions:
            block = self.store.get_session_procedure_block(user_id=user_id, session_id=sess_id)
            proc_items_in_block = [
                m for m in block
                if m.get("is_procedural", 0) or is_procedural_content(m.get("content", ""))
            ]
            for m in proc_items_in_block:
                if m["id"] not in seen_proc_ids:
                    seen_proc_ids.add(m["id"])
                    procedure_memories.append(m)

        if not procedure_memories:
            return candidates

        is_repair_query = bool(REPAIR_QUERY_PATTERN.search(query))

        # Identify primary match:
        # If repair/fix is asked, prioritize memory with repair action; otherwise pick highest candidate score
        primary_match = None
        if is_repair_query:
            for m in procedure_memories:
                if REPAIR_ACTION_PATTERN.search(m.get("content", "")):
                    primary_match = m
                    break

        if not primary_match:
            primary_match = max(
                procedure_memories,
                key=lambda m: cand_scores.get(m["id"], 0.0),
                default=None
            )

        # Assemble ordered procedure:
        # Primary match first, followed by all sequence steps in chronological msg_index order
        ordered_procedure: List[Dict[str, Any]] = []
        if primary_match:
            ordered_procedure.append(primary_match)

        remaining_steps = [
            m for m in procedure_memories
            if not primary_match or m["id"] != primary_match["id"]
        ]
        remaining_steps.sort(
            key=lambda m: (m.get("session_id", ""), m.get("msg_index", 0), m.get("timestamp_ms", 0))
        )
        ordered_procedure.extend(remaining_steps)

        # Build final candidate list:
        # Procedure block FIRST at the top, then remaining candidates
        results: List[Tuple[Dict[str, Any], float]] = []
        top_base_score = candidates[0][1] * self.execution_boost

        for idx, proc_mem in enumerate(ordered_procedure):
            step_score = top_base_score * (1.0 - (idx * 0.001))
            results.append((proc_mem, step_score))

        for mem, score in candidates:
            if mem["id"] not in seen_proc_ids:
                results.append((mem, score))

        return results[:max(top_k, len(candidates))]
