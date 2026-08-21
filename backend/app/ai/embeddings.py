"""Embeddings with a zero-dependency offline fallback.

Two implementations behind one interface:

* :class:`RemoteEmbedder` — calls any OpenAI-compatible ``/embeddings`` endpoint
  (OpenAI, Ollama, a self-hosted server) when ``EMBEDDINGS_*`` env vars are set.
* :class:`LocalHashingEmbedder` — a deterministic hashed bag-of-tokens embedder
  (token unigrams + character trigrams, L2-normalised). No model download, no
  network, fully reproducible. Cosine similarity tracks lexical overlap, which
  — combined with BM25 in the hybrid retriever — gives genuinely useful ranking
  offline. Swapping in real embeddings only improves quality; nothing else
  changes.

The factory :func:`get_embedder` picks based on config.
"""

from __future__ import annotations

import hashlib
import re
from functools import lru_cache

import httpx
import numpy as np

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)

_TOKEN_RE = re.compile(r"[a-z0-9]+")


class Embedder:
    """Abstract embedder interface."""

    dim: int

    def embed(self, text: str) -> list[float]:
        raise NotImplementedError

    def embed_batch(self, texts: list[str]) -> list[list[float]]:
        return [self.embed(t) for t in texts]


class LocalHashingEmbedder(Embedder):
    """Deterministic hashed-feature embedder (offline, dependency-free)."""

    def __init__(self, dim: int | None = None) -> None:
        self.dim = dim or settings.embedding_dim

    def _hash(self, token: str) -> int:
        digest = hashlib.blake2b(token.encode("utf-8"), digest_size=8).digest()
        return int.from_bytes(digest, "little") % self.dim

    def embed(self, text: str) -> list[float]:
        vec = np.zeros(self.dim, dtype=np.float32)
        tokens = _TOKEN_RE.findall(text.lower())
        for tok in tokens:
            vec[self._hash(tok)] += 1.0
            # character trigrams add sub-word robustness (plurals, typos)
            padded = f"#{tok}#"
            for i in range(len(padded) - 2):
                vec[self._hash("_" + padded[i : i + 3])] += 0.5
        norm = np.linalg.norm(vec)
        if norm > 0:
            vec /= norm
        return vec.tolist()


class RemoteEmbedder(Embedder):
    """Calls an OpenAI-compatible embeddings endpoint."""

    def __init__(self) -> None:
        self.model = settings.embeddings_model
        self.base_url = settings.embeddings_base_url.rstrip("/")
        self.api_key = settings.embeddings_api_key
        # Probed lazily on first call; assume 1536 for text-embedding-3-small.
        self.dim = 1536

    def embed_batch(self, texts: list[str]) -> list[list[float]]:
        resp = httpx.post(
            f"{self.base_url}/embeddings",
            headers={"Authorization": f"Bearer {self.api_key}"},
            json={"model": self.model, "input": texts},
            timeout=settings.llm_timeout_seconds,
        )
        resp.raise_for_status()
        data = resp.json()["data"]
        vectors = [item["embedding"] for item in sorted(data, key=lambda d: d["index"])]
        if vectors:
            self.dim = len(vectors[0])
        return vectors

    def embed(self, text: str) -> list[float]:
        return self.embed_batch([text])[0]


@lru_cache(maxsize=1)
def get_embedder() -> Embedder:
    if settings.use_remote_embeddings:
        logger.info("Using remote embeddings model=%s", settings.embeddings_model)
        return RemoteEmbedder()
    logger.info("Using local deterministic embedder dim=%s", settings.embedding_dim)
    return LocalHashingEmbedder()
