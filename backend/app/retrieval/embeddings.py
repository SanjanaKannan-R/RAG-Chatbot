import os
import math
from abc import ABC, abstractmethod
from typing import List, Optional

class BaseEmbeddingProvider(ABC):
    """Abstract base class for pluggable embedding models."""
    
    @abstractmethod
    def embed_text(self, text: str) -> List[float]:
        pass

    @abstractmethod
    def embed_batch(self, texts: List[str]) -> List[List[float]]:
        pass

    @property
    @abstractmethod
    def dimension(self) -> int:
        pass


class SentenceTransformerProvider(BaseEmbeddingProvider):
    """Local, free sentence-transformers embedding provider."""

    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        from sentence_transformers import SentenceTransformer
        self._model = SentenceTransformer(model_name)
        self._dim = self._model.get_sentence_embedding_dimension()

    @property
    def dimension(self) -> int:
        return self._dim

    def embed_text(self, text: str) -> List[float]:
        emb = self._model.encode(text, convert_to_numpy=True)
        return emb.tolist()

    def embed_batch(self, texts: List[str]) -> List[List[float]]:
        if not texts:
            return []
        embs = self._model.encode(texts, convert_to_numpy=True)
        return [e.tolist() for e in embs]


class OpenAIEmbeddingProvider(BaseEmbeddingProvider):
    """OpenAI embeddings provider (e.g. text-embedding-3-small)."""

    def __init__(self, api_key: Optional[str] = None, model: str = "text-embedding-3-small", dimensions: int = 384):
        import openai
        self._client = openai.OpenAI(api_key=api_key or os.getenv("OPENAI_API_KEY"))
        self._model = model
        self._dimensions = dimensions

    @property
    def dimension(self) -> int:
        return self._dimensions

    def embed_text(self, text: str) -> List[float]:
        resp = self._client.embeddings.create(
            input=[text],
            model=self._model,
            dimensions=self._dimensions
        )
        return resp.data[0].embedding

    def embed_batch(self, texts: List[str]) -> List[List[float]]:
        if not texts:
            return []
        resp = self._client.embeddings.create(
            input=texts,
            model=self._model,
            dimensions=self._dimensions
        )
        return [d.embedding for d in resp.data]


class DeterministicLocalProvider(BaseEmbeddingProvider):
    """
    Lightweight, dependency-free local fallback embedding provider.
    Uses TF-IDF hashed bag-of-subwords + cosine normalization.
    Ensures the application works instantly offline and during CI/testing without downloading heavy weights.
    """

    def __init__(self, dimension: int = 384):
        self._dim = dimension

    @property
    def dimension(self) -> int:
        return self._dim

    def _hash_embed(self, text: str) -> List[float]:
        import hashlib
        vec = [0.0] * self._dim
        words = text.lower().replace("\n", " ").split()
        if not words:
            return vec
        
        # Unigrams and bigrams
        tokens = words[:]
        for i in range(len(words) - 1):
            tokens.append(f"{words[i]}_{words[i+1]}")
            
        for token in tokens:
            h = int(hashlib.md5(token.encode("utf-8")).hexdigest(), 16)
            idx = h % self._dim
            sign = 1.0 if ((h >> 8) & 1) else -1.0
            vec[idx] += sign

        # L2 normalize
        norm = math.sqrt(sum(v * v for v in vec))
        if norm > 1e-9:
            vec = [v / norm for v in vec]
        return vec

    def embed_text(self, text: str) -> List[float]:
        return self._hash_embed(text)

    def embed_batch(self, texts: List[str]) -> List[List[float]]:
        return [self._hash_embed(t) for t in texts]


def get_embedding_provider() -> BaseEmbeddingProvider:
    """
    Factory function returning the configured embedding provider based on .env
    Options: 'sentence-transformers', 'openai', 'local'
    Default: 'sentence-transformers' (with fallback to deterministic local if not yet downloaded)
    """
    provider_name = os.getenv("EMBEDDING_PROVIDER", "sentence-transformers").lower()

    if provider_name == "openai":
        return OpenAIEmbeddingProvider()
    elif provider_name == "local":
        return DeterministicLocalProvider()
    else:
        # Default: sentence-transformers with graceful fallback
        try:
            return SentenceTransformerProvider()
        except Exception as e:
            # Fallback to deterministic local provider
            print(f"Warning: SentenceTransformerProvider initialization deferred ({e}). Using DeterministicLocalProvider.")
            return DeterministicLocalProvider()
