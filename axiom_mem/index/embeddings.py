import os
import hashlib
import numpy as np
from abc import ABC, abstractmethod
from typing import List, Optional
from axiom_mem import config


class BaseEmbeddingAdapter(ABC):
    @abstractmethod
    def embed_texts(self, texts: List[str]) -> List[np.ndarray]:
        """Embed a batch of texts into normalized numpy arrays."""
        pass

    def embed_query(self, query: str) -> np.ndarray:
        """Embed a single query text."""
        return self.embed_texts([query])[0]


class FastEmbedAdapter(BaseEmbeddingAdapter):
    """
    High-throughput local embedding adapter using FastEmbed ONNX runtime.
    Runs locally on CPU with zero external API calls or network latency.
    """
    def __init__(self, model_name: Optional[str] = None):
        self.model_name = model_name or config.FASTEMBED_MODEL
        from fastembed import TextEmbedding
        self._model = TextEmbedding(model_name=self.model_name)

    def embed_texts(self, texts: List[str]) -> List[np.ndarray]:
        if not texts:
            return []
        # FastEmbed returns a generator of numpy arrays
        embeddings = list(self._model.embed(texts))
        results = []
        for emb in embeddings:
            norm = np.linalg.norm(emb)
            if norm > 1e-9:
                results.append(emb / norm)
            else:
                results.append(emb)
        return results


class OpenAIEmbeddingAdapter(BaseEmbeddingAdapter):
    """
    API adapter conforming to AML academic board constraint:
    Uses text-embedding-v4 / text-embedding-3-small via OpenAI-compatible API.
    """
    def __init__(self, model: Optional[str] = None, api_key: Optional[str] = None, base_url: Optional[str] = None):
        self.model = model or config.TEXT_EMBEDDING_MODEL
        self.api_key = api_key or config.OPENAI_API_KEY
        self.base_url = base_url or config.OPENAI_BASE_URL or None

        try:
            import httpx
            self._client = httpx.Client(
                base_url=self.base_url or "https://api.openai.com/v1",
                headers={"Authorization": f"Bearer {self.api_key}"},
                timeout=20.0
            )
        except Exception:
            self._client = None

    def embed_texts(self, texts: List[str]) -> List[np.ndarray]:
        if not texts or not self._client or not self.api_key:
            # Fallback to local if no API key is set
            return HashEmbeddingAdapter().embed_texts(texts)

        try:
            resp = self._client.post(
                "/embeddings",
                json={"input": texts, "model": self.model}
            )
            resp.raise_for_status()
            data = resp.json()["data"]
            data.sort(key=lambda x: x["index"])
            results = []
            for item in data:
                vec = np.array(item["embedding"], dtype=np.float32)
                norm = np.linalg.norm(vec)
                results.append(vec / norm if norm > 1e-9 else vec)
            return results
        except Exception as e:
            # Graceful fallback to avoid pipeline disruption
            return HashEmbeddingAdapter().embed_texts(texts)


class HashEmbeddingAdapter(BaseEmbeddingAdapter):
    """
    Deterministic feature hashing vectorizer (384-dim).
    Used as an ultra-fast, zero-dependency offline fallback.
    """
    def __init__(self, dim: int = 384):
        self.dim = dim

    def embed_texts(self, texts: List[str]) -> List[np.ndarray]:
        vectors = []
        for text in texts:
            vec = np.zeros(self.dim, dtype=np.float32)
            words = text.lower().split()
            if not words:
                vectors.append(vec)
                continue
            for word in words:
                idx = int(hashlib.md5(word.encode()).hexdigest(), 16) % self.dim
                vec[idx] += 1.0
            norm = np.linalg.norm(vec)
            if norm > 1e-9:
                vec /= norm
            vectors.append(vec)
        return vectors


_GLOBAL_ADAPTER: Optional[BaseEmbeddingAdapter] = None


def get_embedding_adapter() -> BaseEmbeddingAdapter:
    global _GLOBAL_ADAPTER
    if _GLOBAL_ADAPTER is not None:
        return _GLOBAL_ADAPTER

    provider = config.EMBEDDING_PROVIDER
    if provider == "openai" and config.OPENAI_API_KEY:
        try:
            _GLOBAL_ADAPTER = OpenAIEmbeddingAdapter()
            return _GLOBAL_ADAPTER
        except Exception:
            pass

    if provider in ("fastembed", "local"):
        try:
            _GLOBAL_ADAPTER = FastEmbedAdapter()
            return _GLOBAL_ADAPTER
        except Exception:
            pass

    _GLOBAL_ADAPTER = HashEmbeddingAdapter()
    return _GLOBAL_ADAPTER
