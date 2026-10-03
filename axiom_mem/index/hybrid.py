import numpy as np
from typing import List, Dict, Any, Tuple
from axiom_mem import config
from axiom_mem.store.db import SQLiteStore
from axiom_mem.index.embeddings import BaseEmbeddingAdapter


class HybridIndex:
    """
    Hybrid Retrieval Engine combining:
    1. BM25 exact lexical matching via SQLite FTS5
    2. Dense semantic vector similarity
    3. Reciprocal Rank Fusion (RRF)
    Strictly isolated per user_id.
    """
    def __init__(self, store: SQLiteStore, embedder: BaseEmbeddingAdapter):
        self.store = store
        self.embedder = embedder

    def search_candidates(
        self,
        user_id: str,
        query: str,
        top_k: int = 100,
        candidate_pool_size: int = 250
    ) -> List[Tuple[Dict[str, Any], float]]:
        """
        Retrieve and fuse candidates from BM25 and Dense channels.
        Returns list of (memory_dict, fused_score) sorted descending by score.
        """
        # 1. Lexical BM25 Channel
        bm25_results = self.store.search_bm25(user_id=user_id, query=query, limit=candidate_pool_size)
        bm25_ranks: Dict[str, int] = {mem_id: rank + 1 for rank, (mem_id, _) in enumerate(bm25_results)}

        # 2. Dense Semantic Channel
        query_vector = self.embedder.embed_query(query)
        user_embs = self.store.get_user_embeddings(user_id=user_id, limit=candidate_pool_size)

        dense_ranks: Dict[str, int] = {}
        if user_embs:
            try:
                emb_ids, emb_blobs = zip(*user_embs)
                dim = len(query_vector)
                matrix = np.frombuffer(b"".join(emb_blobs), dtype=np.float32).reshape(len(emb_ids), dim)
                sims = np.dot(matrix, query_vector)
                top_indices = np.argsort(-sims)[:candidate_pool_size]
                for rank, idx in enumerate(top_indices):
                    sim_val = float(sims[idx])
                    if sim_val >= config.MIN_RELEVANCE_SIMILARITY:
                        dense_ranks[emb_ids[idx]] = rank + 1
            except Exception:
                pass

        # 3. Reciprocal Rank Fusion (RRF)
        all_candidate_ids = set(bm25_ranks.keys()).union(set(dense_ranks.keys()))
        if not all_candidate_ids:
            return []

        k = config.RRF_K
        bm25_w = config.BM25_WEIGHT
        dense_w = config.DENSE_WEIGHT

        scored_ids: List[Tuple[str, float]] = []
        for mem_id in all_candidate_ids:
            score = 0.0
            if mem_id in bm25_ranks:
                score += bm25_w * (1.0 / (k + bm25_ranks[mem_id]))
            if mem_id in dense_ranks:
                score += dense_w * (1.0 / (k + dense_ranks[mem_id]))
            scored_ids.append((mem_id, score))

        scored_ids.sort(key=lambda x: (round(x[1], 8), x[0]), reverse=True)
        top_ids = [m_id for m_id, _ in scored_ids[:candidate_pool_size]]


        # Lazy fetch: only read full rows for the top fused candidate IDs
        memories_by_id = self.store.get_memories_by_ids(user_id, top_ids)

        fused_items: List[Tuple[Dict[str, Any], float]] = []
        for mem_id, score in scored_ids[:candidate_pool_size]:
            mem = memories_by_id.get(mem_id)
            if mem:
                fused_items.append((mem, score))

        return fused_items
