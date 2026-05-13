"""Gemini embedder for neo4j_graphrag.

Wraps google-genai's embed_content API to conform to neo4j_graphrag's
`Embedder` abstract interface (which only requires `embed_query(text: str) -> list[float]`).

Used by `agent_zot.clients.neo4j_graphrag.Neo4jGraphRAGClient` when the
project config selects `embedding_provider: "gemini"` or when
`AGENT_ZOT_USE_GEMINI=1` is set in the environment.

Phase 2 of the Gemini RAG migration — see
`~/toolboxes/PAI-stack/PAI-OS/runtime/ops/gemini-rag-migration-plan.md`.
"""
from __future__ import annotations

import logging
import os
import time
from typing import Optional

from neo4j_graphrag.embeddings.base import Embedder

logger = logging.getLogger(__name__)

DEFAULT_MODEL = "gemini-embedding-2"
DEFAULT_DIMENSIONS = 3072


class GeminiEmbeddings(Embedder):
    """Gemini embedder conforming to neo4j_graphrag's Embedder interface.

    The base class only requires `embed_query(text)`, but a single-text
    helper is fragile under load. We also accept `embed_batch(texts)` for
    callers that batch up work (graphiti-core's create_batch path uses
    that). Both flavours respect a `batch_size=1` floor because
    gemini-embedding-2 returns a single vector when given a list-of-texts
    (graphiti issue #1467); we work around that by always issuing one
    embed call per text.
    """

    def __init__(
        self,
        model: str = DEFAULT_MODEL,
        api_key: Optional[str] = None,
        output_dimensionality: Optional[int] = DEFAULT_DIMENSIONS,
        max_retries: int = 3,
    ):
        try:
            import google.genai as genai
            from google.genai import types as genai_types
        except ImportError as e:
            raise ImportError(
                "google-genai is required for GeminiEmbeddings. "
                "Install with: pip install google-genai"
            ) from e

        self._genai = genai
        self._genai_types = genai_types

        resolved_key = api_key or os.getenv("GOOGLE_API_KEY")
        if not resolved_key:
            raise ValueError(
                "GeminiEmbeddings requires an API key. Pass api_key= or set GOOGLE_API_KEY."
            )

        self.model = model
        self.output_dimensionality = output_dimensionality
        self.max_retries = max_retries
        self.client = genai.Client(api_key=resolved_key)

        logger.info(
            f"GeminiEmbeddings initialised — model={model} dim={output_dimensionality}"
        )

    def _embed_one(self, text: str) -> list[float]:
        """Embed a single text with retry-on-transient. One API call per text."""
        last_err: Optional[Exception] = None
        for attempt in range(1, self.max_retries + 1):
            try:
                config = None
                if self.output_dimensionality is not None:
                    config = self._genai_types.EmbedContentConfig(
                        output_dimensionality=self.output_dimensionality
                    )
                result = self.client.models.embed_content(
                    model=self.model,
                    contents=text,
                    config=config,
                )
                if not result.embeddings or not result.embeddings[0].values:
                    raise ValueError(
                        f"Gemini returned no embeddings for input (model={self.model})"
                    )
                return list(result.embeddings[0].values)
            except Exception as e:
                last_err = e
                msg = str(e)
                transient = (
                    "503" in msg
                    or "429" in msg
                    or "UNAVAILABLE" in msg
                    or "RESOURCE_EXHAUSTED" in msg
                    or "DEADLINE_EXCEEDED" in msg
                    or "ConnectError" in msg
                )
                if attempt < self.max_retries and transient:
                    backoff = 2 ** attempt
                    logger.warning(
                        f"GeminiEmbeddings transient error attempt {attempt}/{self.max_retries}: "
                        f"{type(e).__name__} — retrying in {backoff}s"
                    )
                    time.sleep(backoff)
                    continue
                break
        assert last_err is not None
        raise last_err

    def embed_query(self, text: str) -> list[float]:
        return self._embed_one(text)

    def embed_batch(self, texts: list[str]) -> list[list[float]]:
        """Sequential per-text — no parallelism here.

        Callers that need parallelism should use asyncio + the async client;
        this batch helper exists so neo4j_graphrag retriever code that
        passes lists doesn't blow up.
        """
        return [self._embed_one(t) for t in texts]
