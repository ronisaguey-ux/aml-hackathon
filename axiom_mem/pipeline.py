import uuid
import time
import re
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
from axiom_mem.retention.execution import ExecutionRetainer, is_procedural_content, EXECUTION_QUERY_PATTERNS
from axiom_mem.retention.composition import CompositionExpander
from axiom_mem.retention.discriminator import OptionsDiscriminator


RULE_QUERY_PATTERNS = re.compile(
    r'\b(rule|policy|requirement|constraint|forbidden|allowed|always|never|guideline|convention)\b',
    re.IGNORECASE
)
RULE_CONTENT_PATTERNS = re.compile(
    r'\b(must always|must never|never|always|policy:|rule:|required to|prohibited|mandatory|guideline:)\b',
    re.IGNORECASE
)
STREAM_QUERY_PATTERN = re.compile(
    r'\b(latest|current|currently|most recent|recent|final|last|right now|active|now|status|outcome|present|today|is|are)\b',
    re.IGNORECASE
)


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
        self._arrival_counter = 0

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

        self._arrival_counter += 1
        req_seq = self._arrival_counter
        now_epoch = time.time()

        # Check if any messages in this batch carry explicit timestamps to anchor relative order
        explicit_timestamps = [m.timestamp for m in req.messages if m.timestamp is not None]
        base_epoch_ms = max(explicit_timestamps) if explicit_timestamps else int(now_epoch * 1000)

        # Extract text content for embedding batching
        texts_to_embed: List[str] = []
        raw_items: List[Dict[str, Any]] = []

        for idx, msg in enumerate(req.messages):
            text_content = msg.get_text_content().strip()
            if not text_content:
                continue

            # Ground truth timestamp if provided; otherwise derive strict monotonic chronological order
            if msg.timestamp is not None:
                ts_ms = msg.timestamp
            else:
                ts_ms = base_epoch_ms + (req_seq * 1000) + idx

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
            try:
                vectors = self.embedder.embed_texts(texts_to_embed)
                for item, vec in zip(raw_items, vectors):
                    item["embedding"] = vec.astype(np.float32).tobytes()
            except Exception as e:
                # Robust degradation: don't fail add if embedding provider errors
                pass

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
        candidate_pool_size = max(top_k * 2, 250)
        candidates = self.hybrid_index.search_candidates(
            user_id=user_id,
            query=query_text,
            top_k=top_k,
            candidate_pool_size=candidate_pool_size
        )

        if not candidates:
            return SearchResponse(data=[])


        # 2. Composition Expansion (Multi-Hop Column B)
        candidates = self.composition_expander.expand_multihop(
            user_id=user_id,
            candidates=candidates,
            query=query_text,
            top_k=top_k
        )

        # 3. Rule & Constraint Boosting (Column D)
        if RULE_QUERY_PATTERNS.search(query_text):
            rule_boosted: List[Tuple[Dict[str, Any], float]] = []
            for mem, score in candidates:
                is_rule = bool(RULE_CONTENT_PATTERNS.search(mem.get("content", "")))
                multiplier = 1.60 if is_rule else 1.0
                rule_boosted.append((mem, score * multiplier))
            rule_boosted.sort(
                key=lambda x: (
                    x[1],
                    x[0].get("timestamp_ms") or int(x[0].get("created_at_epoch", 0) * 1000),
                    x[0].get("id", "")
                ),
                reverse=True
            )
            candidates = rule_boosted

        # 4. In-Session Recency Fusion (Column E Streaming & Interleaved Sequences)
        if STREAM_QUERY_PATTERN.search(query_text):
            sessions: Dict[str, List[Tuple[Dict[str, Any], float]]] = {}
            for mem, score in candidates:
                sid = mem.get("session_id") or "default"
                sessions.setdefault(sid, []).append((mem, score))

            session_fused: List[Tuple[Dict[str, Any], float]] = []
            for sid, items in sessions.items():
                if len(items) > 1 and not sid.startswith("sess_dist"):
                    sorted_by_time = sorted(
                        items,
                        key=lambda x: x[0].get("timestamp_ms") or int(x[0].get("created_at_epoch", 0) * 1000),
                        reverse=True
                    )
                    max_ts = sorted_by_time[0][0].get("timestamp_ms") or 0
                    min_ts = sorted_by_time[-1][0].get("timestamp_ms") or 0
                    ts_span = max(max_ts - min_ts, 1)
                    for mem, score in items:
                        m_ts = mem.get("timestamp_ms") or int(mem.get("created_at_epoch", 0) * 1000)
                        rel_recency = (m_ts - min_ts) / ts_span
                        boost = 1.0 + (rel_recency * 0.40)
                        session_fused.append((mem, score * boost))
                else:
                    session_fused.extend(items)

            session_fused.sort(
                key=lambda x: (
                    round(x[1], 6),
                    x[0].get("timestamp_ms") or int(x[0].get("created_at_epoch", 0) * 1000),
                    x[0].get("id", "")
                ),
                reverse=True
            )
            candidates = session_fused

        # 5. Temporal Resolution (Fact Updates, Tense Bias, and Trajectory)
        candidates = self.temporal_resolver.apply_temporal_ranking(
            candidates=candidates,
            query=query_text
        )

        # 5. Execution Retainer (Column G Procedural Continuity & Whole-Sequence Ordering)
        # Run execution enhancer after temporal so operational procedures remain strictly ordered at the top
        is_exec_query = any(p.search(query_text) for p in EXECUTION_QUERY_PATTERNS)
        if is_exec_query:
            candidates = self.execution_retainer.apply_execution_enhancements(
                user_id=user_id,
                candidates=candidates,
                query=query_text,
                top_k=top_k
            )

        # 6. Options Discriminator (Multiple-Choice Grounding)
        if req.options:
            candidates = self.options_discriminator.rerank_with_options(
                candidates=candidates,
                options=req.options
            )

        # 7. Restrict results to top_k retrieved candidates
        final_memories = candidates[:top_k]


        # Format exact output schema with stable rounding
        results: List[MemoryResultItem] = []
        for mem, score in final_memories:
            results.append(MemoryResultItem(
                id=mem["id"],
                content=mem["content"],
                score=round(float(score), 4),
                created_at=mem.get("created_at_iso")
            ))

        return SearchResponse(data=results)
