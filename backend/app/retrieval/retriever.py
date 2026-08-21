"""Hybrid retriever with source-authority + freshness weighting and MMR.

Pipeline (per query, already RBAC-filtered by the repository):
    1. Candidate load  — visible chunks only (account + audience scoped).
    2. Lexical score   — BM25 over chunk text.
    3. Semantic score  — cosine over embeddings.
    4. Blend           — ``alpha·semantic + (1-alpha)·lexical`` (min-max normed).
    5. Weight          — × authority factor × freshness factor (deprecated docs
                          are surfaced but down-weighted, never dropped, so the
                          agent can *see* and explain a conflict).
    6. MMR             — greedy re-rank for relevance/diversity trade-off.
    7. Confidence      — from top score, score margin, and evidence agreement.

Every score component is returned for explainability — the UI shows *why* each
source ranked where it did.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
from rank_bm25 import BM25Okapi

from app.ai.embeddings import get_embedder
from app.core.clock import ensure_ist, reference_now
from app.core.config import settings
from app.core.constants import SourceType, authority_weight
from app.models.knowledge import DocumentChunk


@dataclass
class ScoredChunk:
    """A retrieved chunk with a full, explainable score breakdown."""

    chunk_id: int
    document_code: str
    title: str
    heading: str
    source_type: str
    status: str
    authority_rank: int
    content: str
    source_file: str | None
    scores: dict = field(default_factory=dict)

    def citation(self, index: int) -> dict:
        return {
            "marker": f"S{index}",
            "document_code": self.document_code,
            "title": self.title,
            "heading": self.heading,
            "source_type": self.source_type,
            "status": self.status,
            "authority_rank": self.authority_rank,
            "source_file": self.source_file,
            "relevance": round(self.scores.get("final", 0.0), 3),
        }


def _tokenize(text: str) -> list[str]:
    import re

    return re.findall(r"[a-z0-9]+", text.lower())


def _minmax(values: list[float]) -> list[float]:
    if not values:
        return []
    lo, hi = min(values), max(values)
    if hi - lo < 1e-9:
        return [0.5 for _ in values]  # all equal → neutral
    return [(v - lo) / (hi - lo) for v in values]


def _freshness_factor(effective_date, status: str) -> float:
    """Newer/current documents score higher; deprecated ones are halved."""
    factor = 1.0
    if effective_date is not None:
        age_days = max(0, (reference_now() - ensure_ist(effective_date)).days)
        factor = max(0.5, 1.0 - max(0, age_days - 180) / 2000.0)
    if status == "deprecated":
        factor *= 0.5
    return factor


class HybridRetriever:
    def __init__(self, chunks: list[DocumentChunk]) -> None:
        self._chunks = chunks
        self._embedder = get_embedder()
        self._tokenized = [_tokenize(c.content + " " + (c.heading or "")) for c in chunks]
        self._bm25 = BM25Okapi(self._tokenized) if chunks else None
        self._matrix = (
            np.array([c.embedding for c in chunks if c.embedding is not None], dtype=np.float32)
            if any(c.embedding for c in chunks)
            else None
        )

    def retrieve(
        self, query: str, *, top_k: int | None = None
    ) -> tuple[list[ScoredChunk], float]:
        top_k = top_k or settings.retrieval_top_k
        if not self._chunks or self._bm25 is None:
            return [], 0.0

        # --- lexical ------------------------------------------------------
        bm25_scores = list(self._bm25.get_scores(_tokenize(query)))

        # --- semantic -----------------------------------------------------
        q_vec = np.array(self._embedder.embed(query), dtype=np.float32)
        vec_scores: list[float] = []
        for chunk in self._chunks:
            if chunk.embedding is None:
                vec_scores.append(0.0)
                continue
            c_vec = np.array(chunk.embedding, dtype=np.float32)
            denom = (np.linalg.norm(q_vec) * np.linalg.norm(c_vec)) or 1.0
            vec_scores.append(float(np.dot(q_vec, c_vec) / denom))

        bm25_n, vec_n = _minmax(bm25_scores), _minmax(vec_scores)
        alpha = settings.hybrid_alpha

        scored: list[ScoredChunk] = []
        for i, chunk in enumerate(self._chunks):
            relevance = alpha * vec_n[i] + (1 - alpha) * bm25_n[i]
            try:
                auth = authority_weight(SourceType(chunk.source_type))
            except ValueError:
                auth = 0.4
            fresh = _freshness_factor(chunk.effective_date, chunk.status)
            final = relevance * (0.6 + 0.4 * auth) * fresh
            scored.append(
                ScoredChunk(
                    chunk_id=chunk.id,
                    document_code=chunk.meta.get("document_code", ""),
                    title=chunk.meta.get("title", ""),
                    heading=chunk.heading,
                    source_type=chunk.source_type,
                    status=chunk.status,
                    authority_rank=chunk.authority_rank,
                    content=chunk.content,
                    source_file=chunk.meta.get("source_file"),
                    scores={
                        "lexical": round(bm25_n[i], 3),
                        "semantic": round(vec_n[i], 3),
                        "relevance": round(relevance, 3),
                        "authority": round(auth, 3),
                        "freshness": round(fresh, 3),
                        "final": round(final, 3),
                    },
                )
            )

        # Candidate shortlist then MMR for diversity.
        scored.sort(key=lambda s: s.scores["final"], reverse=True)
        candidates = scored[: settings.retrieval_candidate_k]
        selected = self._mmr(query, candidates, top_k)
        confidence = self._confidence(selected)
        return selected, confidence

    def _mmr(self, query: str, candidates: list[ScoredChunk], k: int) -> list[ScoredChunk]:
        """Maximal Marginal Relevance re-ranking for relevance/diversity."""
        if len(candidates) <= k:
            return candidates
        lam = settings.mmr_lambda
        embedder = self._embedder
        cand_vecs = {c.chunk_id: np.array(embedder.embed(c.content), dtype=np.float32) for c in candidates}

        def cos(a, b):
            denom = (np.linalg.norm(a) * np.linalg.norm(b)) or 1.0
            return float(np.dot(a, b) / denom)

        selected: list[ScoredChunk] = []
        pool = candidates.copy()
        while pool and len(selected) < k:
            best, best_val = None, -1e9
            for cand in pool:
                relevance = cand.scores["final"]
                diversity = max(
                    (cos(cand_vecs[cand.chunk_id], cand_vecs[s.chunk_id]) for s in selected),
                    default=0.0,
                )
                mmr_val = lam * relevance - (1 - lam) * diversity
                if mmr_val > best_val:
                    best, best_val = cand, mmr_val
            selected.append(best)
            pool.remove(best)
        return selected

    @staticmethod
    def _confidence(selected: list[ScoredChunk]) -> float:
        """Retrieval confidence in [0,1] from top score, margin, and support."""
        if not selected:
            return 0.0
        top = selected[0].scores["final"]
        margin = top - (selected[1].scores["final"] if len(selected) > 1 else 0.0)
        support = min(1.0, len([s for s in selected if s.scores["final"] > 0.3 * top]) / 3.0)
        raw = 0.6 * top + 0.25 * margin + 0.15 * support
        return round(max(0.0, min(1.0, raw)), 3)


def build_context_block(chunks: list[ScoredChunk]) -> str:
    """Render selected evidence into a compact, marker-tagged block for the LLM."""
    lines = []
    for i, ch in enumerate(chunks, start=1):
        tag = f"[S{i}] {ch.title} — {ch.heading}"
        status = " (DEPRECATED — context only)" if ch.status == "deprecated" else ""
        lines.append(f"{tag}{status}\n{ch.content}")
    return "\n\n".join(lines)
