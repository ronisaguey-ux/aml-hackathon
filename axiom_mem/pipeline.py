import uuid
import time
import numpy as np
from typing import List, Dict, Any, Optional

from axiom_mem.schemas import (
    AddRequest,
    AddResponse,
    SearchRequest,
    SearchResponse,
    MemoryResultItem,
)
from axiom_mem.store.db import SQLiteStore
from axiom_mem.index.embeddings import BaseEmbeddingAdapter, get_embedding_adapter
from axiom_mem.index.hybrid import HybridIndex
from axiom_mem.retention.temporal import TemporalResolver, format_iso_timestamp
from axiom_mem.retention.execution import ExecutionRetainer, is_procedural_content
from axiom_mem.retention.composition import CompositionExpander
from axiom_mem.retention.discriminator import OptionsDiscriminator


class MemoryPipeline:
    """
    Unified Memory Pipeline coordinating durable storage, hybrid retrieval,
    and the multi-capability retention layer.
    """
    def __init__(
        self,
        store: SQLiteStore,
        embedder: Optional[BaseEmbeddingAdapter] = None
    ):
        self.store = store
        self.embedder = embedder or get_embedding_adapter()
        self.hybrid_index = HybridIndex(self.store, self.embedder)
        self.temporal_resolver = TemporalResolver()
        self.execution_retainer = ExecutionRetainer(self.store)
        self.composition_expander = CompositionExpander(self.store)
        self.options_discriminator = OptionsDiscriminator()

    def add(self, req: AddRequest) -> AddResponse:
        # 1. Idempotency Check
        if self.store.is_request_seen(req.request_id):
            return AddResponse(
                success=True,
                request_id=req.request_id,
                user_id=req.user_id,
                session_id=req.session_id
            )

        # Record request immediately
        self.store.record_request(req.request_id, req.user_id, req.session_id)

        if not req.messages:
            return AddResponse(
                success=True,
                request_id=req.request_id,
                user_id=req.user_id,
                session_id=req.session_id
            )

        now_epoch = time.time()
        now_epoch_ms = int(now_epoch * 1000)

        # Extract text content for embedding batching
        texts_to_embed: List[str] = []
        raw_items: List[Dict[str, Any]] = []

        for idx, msg in enumerate(req.messages):
            text_content = msg.get_text_content().strip()
            if not text_content:
                continue

            ts_ms = msg.timestamp if msg.timestamp is not None else now_epoch_ms
            iso_str = format_iso_timestamp(ts_ms, now_epoch)
            is_proc = 1 if is_procedural_content(text_content) else 0

            # Deterministic, unique, stable memory ID
            mem_id = f"mem_{uuid.uuid5(uuid.NAMESPACE_DNS, f'{req.user_id}:{req.request_id}:{idx}').hex[:16]}"

            raw_items.append({
                "id": mem_id,
                "user_id": req.user_id,
                "session_id": req.session_id,
                "request_id": req.request_id,
                "msg_index": idx,
                "role": msg.role,
                "content": text_content,
                "timestamp_ms": ts_ms,
                "created_at_iso": iso_str,
                "is_procedural": is_proc,
            })
            texts_to_embed.append(text_content)

        # Generate embeddings in single batch for speed
        if texts_to_embed:
            vectors = self.embedder.embed_texts(texts_to_embed)
            for item, vec in zip(raw_items, vectors):
                item["embedding"] = vec.astype(np.float32).tobytes()

        # Synchronously insert and index to disk
        self.store.insert_memories(raw_items)

        return AddResponse(
            success=True,
            request_id=req.request_id,
            user_id=req.user_id,
            session_id=req.session_id
        )

    def search(self, req: SearchRequest) -> SearchResponse:
        query_text = req.get_query_text().strip()
        user_id = req.user_id
        top_k = max(1, req.top_k)

        # If query is completely empty, return recent memories for this user
        if not query_text:
            all_mem = self.store.get_all_memories_for_user(user_id=user_id, limit=top_k)
            return SearchResponse(data=[
                MemoryResultItem(
                    id=m["id"],
                    content=m["content"],
                    score=1.0,
                    created_at=m["created_at_iso"]
                ) for m in all_mem
            ])

        # 1. Hybrid Retrieval (BM25 + Dense via RRF)
        # Fetch a generous candidate pool to allow retention re-ranking
        candidate_pool_size = max(top_k * 2, 250)
        candidates = self.hybrid_index.search_candidates(
            user_id=user_id,
            query=query_text,
            top_k=top_k,
            candidate_pool_size=candidate_pool_size
        )

        if not candidates:
            # Check if user has any memories stored at all
            all_mem = self.store.get_all_memories_for_user(user_id=user_id, limit=top_k)
            return SearchResponse(data=[
                MemoryResultItem(
                    id=m["id"],
                    content=m["content"],
                    score=0.1,
                    created_at=m["created_at_iso"]
                ) for m in all_mem
            ])

        # 2. Composition Expansion (Multi-Hop Column B)
        candidates = self.composition_expander.expand_multihop(
            user_id=user_id,
            candidates=candidates,
            query=query_text,
            top_k=top_k
        )

        # 3. Execution Retainer (Column G Procedural Continuity)
        candidates = self.execution_retainer.apply_execution_enhancements(
            user_id=user_id,
            candidates=candidates,
            query=query_text,
            top_k=top_k
        )

        # 4. Temporal Resolution (Fact Updates and Recency)
        candidates = self.temporal_resolver.apply_temporal_ranking(
            candidates=candidates,
            query=query_text
        )

        # 5. Options Discriminator (Multiple-Choice Grounding)
        if req.options:
            candidates = self.options_discriminator.rerank_with_options(
                candidates=candidates,
                options=req.options
            )

        # 6. Fill up to top_k if available memories exist
        final_memories = candidates[:top_k]
        if len(final_memories) < top_k:
            existing_ids = {m["id"] for m, _ in final_memories}
            all_user_mem = self.store.get_all_memories_for_user(user_id=user_id, limit=top_k)
            for m in all_user_mem:
                if len(final_memories) >= top_k:
                    break
                if m["id"] not in existing_ids:
                    existing_ids.add(m["id"])
                    final_memories.append((m, 0.001))

        # Format exact output schema
        results: List[MemoryResultItem] = []
        for mem, score in final_memories:
            results.append(MemoryResultItem(
                id=mem["id"],
                content=mem["content"],
                score=round(float(score), 4),
                created_at=mem.get("created_at_iso")
            ))

        return SearchResponse(data=results)
