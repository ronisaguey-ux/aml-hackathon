import re
from typing import List, Dict, Any, Tuple, Set
from axiom_mem import config
from axiom_mem.store.db import SQLiteStore


ENTITY_PATTERN = re.compile(r'\b([A-Z][a-zA-Z0-9_\-\.]{2,}|[a-zA-Z0-9_\-\.]+\/[a-zA-Z0-9_\-\.]+|\b[A-Z]{2,}\b)\b')
COMMON_STOP_WORDS = {
    "The", "This", "That", "There", "Here", "What", "When", "Where", "Which", "Who",
    "How", "Why", "And", "But", "For", "Nor", "Or", "So", "Yet", "After", "Before",
    "Once", "Since", "Until", "When", "Whenever", "While", "Because", "Although",
    "User", "Assistant", "System", "Option", "Answer", "Step", "Policy", "Discussion"
}

QUESTION_TARGET_PATTERN = re.compile(
    r'\b(city|country|state|location|headquarters|headquartered|institute|company|university|director|founder|ceo|author|version|port|email)\b',
    re.IGNORECASE
)


def extract_key_entities(text: str) -> Set[str]:
    """Extract candidate entities and identifiers (capitalized terms, snake_case, CamelCase, file paths)."""
    raw_matches = ENTITY_PATTERN.findall(text)
    entities = {
        m for m in raw_matches
        if m not in COMMON_STOP_WORDS and len(m) > 2
    }
    return entities


class CompositionExpander:
    """
    Multi-Hop Composition Engine (Column B):
    - Identifies bridge entities in top direct candidate hits.
    - Budgets 2-hop graph expansion to strictly prevent dilution.
    - Accords target-entity alignment boost when a linked premise contains
      the specific target entity/attribute requested by the question.
    """
    def __init__(self, store: SQLiteStore, expansion_boost: float = config.COMPOSITION_EXPANSION_BOOST):
        self.store = store
        self.expansion_boost = expansion_boost

    def expand_multihop(
        self,
        user_id: str,
        candidates: List[Tuple[Dict[str, Any], float]],
        query: str,
        top_k: int = 100
    ) -> List[Tuple[Dict[str, Any], float]]:
        if not candidates or len(candidates) < 1:
            return candidates

        existing_ids = {m["id"] for m, _ in candidates}
        query_entities = extract_key_entities(query)
        target_matches = set(QUESTION_TARGET_PATTERN.findall(query.lower()))

        expanded_candidates: List[Tuple[Dict[str, Any], float]] = list(candidates)

        # 1. Expand linked memories for top 3 direct hits
        for parent_mem, parent_score in candidates[:3]:
            content = parent_mem.get("content", "")
            mem_entities = extract_key_entities(content)
            bridge_entities = [e for e in (mem_entities - query_entities) if len(e) > 3]

            for entity in bridge_entities[:2]:
                linked_results = self.store.search_bm25(user_id=user_id, query=entity, limit=2)
                linked_ids = [m_id for m_id, _ in linked_results if m_id not in existing_ids]

                if linked_ids:
                    fetched = self.store.get_memories_by_ids(user_id, linked_ids)
                    for mem_id, linked_mem in fetched.items():
                        if mem_id not in existing_ids:
                            existing_ids.add(mem_id)
                            expanded_candidates.append((linked_mem, parent_score * 0.95))

        # 2. Target Attribute Alignment:
        # If a candidate directly contains words answering the specific target category (e.g. "city", "headquartered"),
        # give it a subtle 1.05x boost so the answer premise ranks #1 with the bridge premise adjacent at #2.
        if target_matches:
            reweighted: List[Tuple[Dict[str, Any], float]] = []
            for mem, score in expanded_candidates:
                mem_content_lower = mem.get("content", "").lower()
                matches_target = any(tm in mem_content_lower for tm in target_matches)
                multiplier = 1.06 if matches_target else 1.0
                reweighted.append((mem, score * multiplier))
            expanded_candidates = reweighted

        # Re-sort descending
        expanded_candidates.sort(
            key=lambda x: (
                round(x[1], 6),
                x[0].get("timestamp_ms") or int(x[0].get("created_at_epoch", 0) * 1000),
                x[0].get("id", "")
            ),
            reverse=True
        )
        return expanded_candidates[:max(top_k, len(candidates))]
