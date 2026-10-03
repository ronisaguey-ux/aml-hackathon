import re
from typing import List, Dict, Any, Tuple
from axiom_mem import config
from axiom_mem.store.db import SQLiteStore

CODE_INDICATORS = [
    re.compile(r'```', re.MULTILINE),
    re.compile(r'\b(def |class |function |import |from |return |const |let |var |fn |pub |impl )\b'),
    re.compile(r'\b(pip |npm |cargo |curl |docker |git |kubectl |pytest |python |bash |mvn |gradle )\b'),
    re.compile(r'(\bTraceback\b|\bException\b|\bError:|\bFailed:\b|\bexit code \d+)'),
]

PROCEDURAL_INDICATORS = [
    re.compile(r'(^\s*\d+[\.\)]\s+|^\s*[-*]\s+)', re.MULTILINE),
    re.compile(r'\b(step \d+|first|second|then|finally|after that|next step|prerequisite)\b', re.IGNORECASE),
    re.compile(r'\b(must always|never|required to|procedure|rule:|guideline:|instruction:)\b', re.IGNORECASE),
]

EXECUTION_QUERY_PATTERNS = [
    re.compile(r'\b(how to|steps?|procedure|instructions?|workflow|run|execute|build|deploy|install)\b', re.IGNORECASE),
    re.compile(r'\b(fix|repair|debug|error|issue|solution|trace|bug|crash|exception)\b', re.IGNORECASE),
    re.compile(r'\b(implement|code|function|script|command|test|rule|policy)\b', re.IGNORECASE),
]


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
    Detects execution intent, preserves procedural continuity, expands sequential dependencies,
    and boosts ordered operational memories so the model can successfully execute rather than just recall.
    """
    def __init__(self, store: SQLiteStore, execution_boost: float = config.EXECUTION_BOOST):
        self.store = store
        self.execution_boost = execution_boost

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

        # 1. Score adjustment: boost procedural evidence if query is operational
        boosted_candidates: List[Tuple[Dict[str, Any], float]] = []
        for mem, score in candidates:
            is_proc = mem.get("is_procedural", 0) or is_procedural_content(mem.get("content", ""))
            
            multiplier = 1.0
            if is_execution_query and is_proc:
                multiplier = self.execution_boost
            elif is_proc:
                # Slight boost even for general queries because structured rules/code are high signal
                multiplier = 1.0 + (self.execution_boost - 1.0) * 0.4

            boosted_candidates.append((mem, score * multiplier))

        boosted_candidates.sort(key=lambda x: x[1], reverse=True)

        if not is_execution_query:
            return boosted_candidates

        # 2. Sequential Expansion:
        # If top procedural memories belong to a multi-turn instruction/flow,
        # fetch their immediately adjacent steps to guarantee uninterrupted execution context.
        existing_ids = {m["id"] for m, _ in boosted_candidates}
        expanded_memories: List[Tuple[Dict[str, Any], float]] = list(boosted_candidates)

        # Look at top-10 candidates for procedural chains
        for mem, parent_score in boosted_candidates[:10]:
            if not mem.get("is_procedural"):
                continue

            session_id = mem.get("session_id")
            msg_idx = mem.get("msg_index")
            if session_id and msg_idx is not None:
                # Fetch preceding step (msg_idx - 1) and following step (msg_idx + 1)
                adjacent = self.store.get_adjacent_session_memories(
                    user_id=user_id,
                    session_id=session_id,
                    min_idx=max(0, msg_idx - 1),
                    max_idx=msg_idx + 1
                )
                for adj_mem in adjacent:
                    if adj_mem["id"] not in existing_ids:
                        existing_ids.add(adj_mem["id"])
                        # Give adjacent step a connected score slightly below parent
                        expanded_memories.append((adj_mem, parent_score * 0.85))

        # Re-sort descending
        expanded_memories.sort(key=lambda x: x[1], reverse=True)
        return expanded_memories[:max(top_k, len(candidates))]
