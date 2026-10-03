import re
from typing import List, Dict, Any, Tuple, Set
from axiom_mem import config
from axiom_mem.store.db import SQLiteStore


ENTITY_PATTERN = re.compile(r'\b[A-Z][a-zA-Z0-9_\-\.]{2,}\b')
COMMON_STOP_WORDS = {
    "The", "This", "That", "There", "Here", "What", "When", "Where", "Which", "Who",
    "How", "Why", "And", "But", "For", "Nor", "Or", "So", "Yet", "After", "Before",
    "Once", "Since", "Until", "When", "Whenever", "While", "Because", "Although",
    "User", "Assistant", "System", "Option", "Answer"
}


def extract_key_entities(text: str) -> Set[str]:
    """Extract candidate entities and identifiers (capitalized terms, snake_case, CamelCase)."""
    raw_matches = ENTITY_PATTERN.findall(text)
    entities = {
        m for m in raw_matches
        if m not in COMMON_STOP_WORDS and len(m) > 2
    }
    return entities


class CompositionExpander:
    """
    Multi-Hop Composition Engine (Column B):
    Identifies bridge entities in top retrieved memories and expands 2-hop relational context
    so that multi-premise reasoning has all required evidence present in the context.
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
        if not candidates or len(candidates) < 2:
            return candidates

        existing_ids = {m["id"] for m, _ in candidates}
        query_entities = extract_key_entities(query)

        # Extract bridge entities from the top 5 direct candidate hits
        bridge_entities: Set[str] = set()
        for mem, _ in candidates[:5]:
            content = mem.get("content", "")
            mem_entities = extract_key_entities(content)
            # Find entities present in the memory that were NOT in the original query
            new_entities = mem_entities - query_entities
            bridge_entities.update(new_entities)

        if not bridge_entities:
            return candidates

        # Limit to top 3 most promising bridge entities
        expanded_candidates: List[Tuple[Dict[str, Any], float]] = list(candidates)
        for entity in list(bridge_entities)[:3]:
            # Perform targeted BM25 search for the bridge entity
            linked_results = self.store.search_bm25(user_id=user_id, query=entity, limit=5)
            linked_ids = [m_id for m_id, _ in linked_results if m_id not in existing_ids]
            
            if linked_ids:
                fetched = self.store.get_memories_by_ids(user_id, linked_ids)
                for mem_id, mem in fetched.items():
                    if mem_id not in existing_ids:
                        existing_ids.add(mem_id)
                        # Score is scaled by expansion boost
                        expanded_candidates.append((mem, 0.05 * self.expansion_boost))

        # Re-sort descending by score
        expanded_candidates.sort(key=lambda x: x[1], reverse=True)
        return expanded_candidates[:max(top_k, len(candidates))]
