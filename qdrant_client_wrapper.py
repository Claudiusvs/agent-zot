"""
Qdrant client for semantic search functionality.

This module provides persistent vector database storage and embedding functions
for semantic search over Zotero libraries using Qdrant.
"""

import json
import os
import uuid
from pathlib import Path
from typing import Dict, List, Optional, Any
import logging

from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance,
    VectorParams,
    SparseVectorParams,
    SparseIndexParams,
    PointStruct,
    Filter,
    FieldCondition,
    MatchValue,
    SparseVector,
    NamedVector,
    NamedSparseVector,
    HnswConfigDiff,
    OptimizersConfigDiff,
    ScalarQuantization,
    ScalarQuantizationConfig,
    ScalarType,
    QuantizationSearchParams,
    PayloadSchemaType
)

logger = logging.getLogger(__name__)


class BM25SparseEmbedding:
    """BM25-based sparse embeddings for hybrid search."""

    def __init__(self):
        """Initialize BM25 encoder."""
        try:
            from sklearn.feature_extraction.text import TfidfVectorizer
            import numpy as np
            self.vectorizer = TfidfVectorizer(
                lowercase=True,
                stop_words='english',
                max_features=10000,
                use_idf=True,
                norm=None  # BM25 doesn't use L2 norm
            )
            self.np = np
            self.fitted = False
        except ImportError:
            raise ImportError("scikit-learn is required for BM25 sparse embeddings")

    def fit(self, documents: List[str]):
        """Fit the BM25 model on documents."""
        if documents:
            self.vectorizer.fit(documents)
            self.fitted = True

    def encode(self, texts: List[str]) -> List[SparseVector]:
        """
        Encode texts to BM25 sparse vectors.

        Args:
            texts: List of texts to encode

        Returns:
            List of SparseVector objects for Qdrant
        """
        if not self.fitted:
            # Fit on the input texts if not already fitted
            self.fit(texts)

        sparse_vectors = []
        tfidf_matrix = self.vectorizer.transform(texts)

        for i in range(tfidf_matrix.shape[0]):
            row = tfidf_matrix[i]
            # Get non-zero indices and values
            indices = row.indices.tolist()
            values = row.data.tolist()

            sparse_vectors.append(SparseVector(
                indices=indices,
                values=values
            ))

        return sparse_vectors


class OpenAIEmbeddingFunction:
    """Custom OpenAI embedding function for Qdrant."""

    def __init__(self, model_name: str = "text-embedding-3-small", api_key: Optional[str] = None):
        self.model_name = model_name
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        if not self.api_key:
            raise ValueError("OpenAI API key is required")

        try:
            import openai
            self.client = openai.OpenAI(api_key=self.api_key)
        except ImportError:
            raise ImportError("openai package is required for OpenAI embeddings")

    def name(self) -> str:
        """Return the name of this embedding function."""
        return "openai"

    def __call__(self, input: List[str]) -> List[List[float]]:
        """Generate embeddings using OpenAI API."""
        response = self.client.embeddings.create(
            model=self.model_name,
            input=input
        )
        return [data.embedding for data in response.data]

    def get_dimension(self) -> int:
        """Get the dimension of embeddings for this model."""
        # text-embedding-3-small: 1536, text-embedding-3-large: 3072
        if "large" in self.model_name:
            return 3072
        return 1536


class GeminiEmbeddingFunction:
    """Custom Gemini embedding function for Qdrant using google-genai."""

    def __init__(self, model_name: str = "models/text-embedding-004", api_key: Optional[str] = None):
        self.model_name = model_name
        self.api_key = api_key or os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
        if not self.api_key:
            raise ValueError("Gemini API key is required")

        try:
            from google import genai
            from google.genai import types
            self.client = genai.Client(api_key=self.api_key)
            self.types = types
        except ImportError:
            raise ImportError("google-genai package is required for Gemini embeddings")

    def name(self) -> str:
        """Return the name of this embedding function."""
        return "gemini"

    def __call__(self, input: List[str]) -> List[List[float]]:
        """Generate embeddings using Gemini API."""
        embeddings = []
        for text in input:
            response = self.client.models.embed_content(
                model=self.model_name,
                contents=[text],
                config=self.types.EmbedContentConfig(
                    task_type="retrieval_document",
                    title="Zotero library document"
                )
            )
            embeddings.append(response.embeddings[0].values)
        return embeddings

    def get_dimension(self) -> int:
        """Get the dimension of embeddings for this model."""
        return 768  # text-embedding-004 produces 768-dimensional embeddings


class DefaultEmbeddingFunction:
    """Default embedding function using sentence-transformers."""

    def __init__(self):
        try:
            from sentence_transformers import SentenceTransformer
            self.model = SentenceTransformer('all-MiniLM-L6-v2')
        except ImportError:
            raise ImportError("sentence-transformers package is required for default embeddings")

    def name(self) -> str:
        """Return the name of this embedding function."""
        return "default"

    def __call__(self, input: List[str]) -> List[List[float]]:
        """Generate embeddings using sentence-transformers."""
        embeddings = self.model.encode(input)
        return embeddings.tolist()

    def get_dimension(self) -> int:
        """Get the dimension of embeddings for this model."""
        return 384  # all-MiniLM-L6-v2 produces 384-dimensional embeddings


class QdrantClientWrapper:
    """Qdrant client for Zotero semantic search."""

    def __init__(self,
                 collection_name: str = "zotero_library",
                 qdrant_url: str = "http://localhost:6333",
                 qdrant_api_key: Optional[str] = None,
                 embedding_model: str = "default",
                 embedding_config: Optional[Dict[str, Any]] = None,
                 enable_hybrid_search: bool = True,
                 enable_quantization: bool = True,
                 hnsw_m: int = 32,
                 hnsw_ef_construct: int = 200,
                 enable_reranking: bool = True):
        """
        Initialize Qdrant client with optimizations.

        Args:
            collection_name: Name of the Qdrant collection
            qdrant_url: URL of the Qdrant server
            qdrant_api_key: API key for Qdrant (if using cloud)
            embedding_model: Model to use for embeddings ('default', 'openai', 'gemini')
            embedding_config: Configuration for the embedding model
            enable_hybrid_search: Enable hybrid search with sparse vectors (default: True)
            enable_quantization: Enable scalar quantization (75% memory savings, default: True)
            hnsw_m: HNSW graph connections per node (default: 32, higher=better recall)
            hnsw_ef_construct: HNSW build-time accuracy (default: 200, higher=better quality)
            enable_reranking: Enable cross-encoder reranking (default: True)
        """
        self.collection_name = collection_name
        self.embedding_model = embedding_model
        self.embedding_config = embedding_config or {}
        self.enable_hybrid_search = enable_hybrid_search
        self.enable_quantization = enable_quantization
        self.hnsw_m = hnsw_m
        self.hnsw_ef_construct = hnsw_ef_construct
        self.enable_reranking = enable_reranking

        # Initialize Qdrant client
        self.client = QdrantClient(
            url=qdrant_url,
            api_key=qdrant_api_key
        )

        # Set up embedding function
        self.embedding_function = self._create_embedding_function()

        # Set up sparse embedding function for hybrid search
        self.sparse_embedding = BM25SparseEmbedding() if enable_hybrid_search else None

        # Initialize cross-encoder for reranking
        self.reranker = None
        if self.enable_reranking:
            self._initialize_reranker()

        # Get or create collection
        try:
            # Check if collection exists
            collections = self.client.get_collections().collections
            collection_exists = any(c.name == self.collection_name for c in collections)

            if not collection_exists:
                # Create collection with appropriate vector size and optimizations
                vector_size = self.embedding_function.get_dimension()

                # Configure HNSW index parameters
                hnsw_config = HnswConfigDiff(
                    m=self.hnsw_m,  # Number of edges per node (higher = better recall)
                    ef_construct=self.hnsw_ef_construct  # Build-time accuracy
                )

                # Configure optimizers
                optimizer_config = OptimizersConfigDiff(
                    indexing_threshold=20000  # Optimize after 20k vectors
                )

                # Configure quantization if enabled
                quantization_config = None
                if self.enable_quantization:
                    quantization_config = ScalarQuantization(
                        scalar=ScalarQuantizationConfig(
                            type=ScalarType.INT8,  # 8-bit quantization
                            quantile=0.99,  # Outlier handling
                            always_ram=True  # Keep quantized vectors in RAM for speed
                        )
                    )

                if enable_hybrid_search:
                    # Create collection with both dense and sparse vectors
                    self.client.create_collection(
                        collection_name=self.collection_name,
                        vectors_config={
                            "dense": VectorParams(
                                size=vector_size,
                                distance=Distance.COSINE,
                                hnsw_config=hnsw_config,
                                quantization_config=quantization_config
                            )
                        },
                        sparse_vectors_config={
                            "sparse": SparseVectorParams(
                                index=SparseIndexParams()
                            )
                        },
                        optimizers_config=optimizer_config
                    )
                    logger.info(f"Created optimized hybrid Qdrant collection '{self.collection_name}':")
                    logger.info(f"  - Dense vectors: {vector_size}D, HNSW(m={self.hnsw_m}, ef={self.hnsw_ef_construct})")
                    logger.info(f"  - Quantization: {'Enabled (INT8)' if self.enable_quantization else 'Disabled'}")
                    logger.info(f"  - Sparse vectors: Enabled (BM25)")
                else:
                    # Create collection with only dense vectors
                    self.client.create_collection(
                        collection_name=self.collection_name,
                        vectors_config=VectorParams(
                            size=vector_size,
                            distance=Distance.COSINE,
                            hnsw_config=hnsw_config,
                            quantization_config=quantization_config
                        ),
                        optimizers_config=optimizer_config
                    )
                    logger.info(f"Created optimized Qdrant collection '{self.collection_name}':")
                    logger.info(f"  - Vectors: {vector_size}D, HNSW(m={self.hnsw_m}, ef={self.hnsw_ef_construct})")
                    logger.info(f"  - Quantization: {'Enabled (INT8)' if self.enable_quantization else 'Disabled'}")

                # Create payload indexes for fast filtering
                self._create_payload_indexes()
            else:
                logger.info(f"Using existing Qdrant collection '{self.collection_name}'")

        except Exception as e:
            logger.error(f"Error initializing Qdrant collection: {e}")
            raise

    def _create_payload_indexes(self):
        """Create indexes on payload fields for fast filtering."""
        try:
            # Index on item_key for fast paper lookups
            self.client.create_payload_index(
                collection_name=self.collection_name,
                field_name="item_key",
                field_schema=PayloadSchemaType.KEYWORD
            )

            # Index on year for temporal filtering
            self.client.create_payload_index(
                collection_name=self.collection_name,
                field_name="year",
                field_schema=PayloadSchemaType.INTEGER
            )

            # Index on item_type for document type filtering
            self.client.create_payload_index(
                collection_name=self.collection_name,
                field_name="item_type",
                field_schema=PayloadSchemaType.KEYWORD
            )

            logger.info("Created payload indexes on item_key, year, item_type")

        except Exception as e:
            logger.warning(f"Error creating payload indexes (may already exist): {e}")

    def _initialize_reranker(self):
        """Initialize cross-encoder model for reranking."""
        try:
            from sentence_transformers import CrossEncoder
            # Use a high-quality cross-encoder for reranking
            self.reranker = CrossEncoder('cross-encoder/ms-marco-MiniLM-L-6-v2')
            logger.info("Initialized cross-encoder reranker (ms-marco-MiniLM-L-6-v2)")
        except ImportError:
            logger.warning("sentence-transformers required for reranking, disabling reranking")
            self.enable_reranking = False
            self.reranker = None
        except Exception as e:
            logger.warning(f"Error initializing reranker: {e}, disabling reranking")
            self.enable_reranking = False
            self.reranker = None

    def _create_embedding_function(self):
        """Create the appropriate embedding function based on configuration."""
        if self.embedding_model == "openai":
            model_name = self.embedding_config.get("model_name", "text-embedding-3-small")
            api_key = self.embedding_config.get("api_key")
            return OpenAIEmbeddingFunction(model_name=model_name, api_key=api_key)

        elif self.embedding_model == "gemini":
            model_name = self.embedding_config.get("model_name", "models/text-embedding-004")
            api_key = self.embedding_config.get("api_key")
            return GeminiEmbeddingFunction(model_name=model_name, api_key=api_key)

        else:
            # Use default sentence-transformers embedding
            return DefaultEmbeddingFunction()

    def add_documents(self,
                     documents: List[str],
                     metadatas: List[Dict[str, Any]],
                     ids: List[str],
                     batch_size: int = 100) -> None:
        """
        Add documents to the collection with batch processing.

        Args:
            documents: List of document texts to embed
            metadatas: List of metadata dictionaries for each document
            ids: List of unique IDs for each document
            batch_size: Number of documents to process in each batch (default: 100)
        """
        try:
            total_docs = len(documents)
            mode = "hybrid" if self.enable_hybrid_search else "dense"

            # Process in batches for better performance
            for batch_start in range(0, total_docs, batch_size):
                batch_end = min(batch_start + batch_size, total_docs)
                batch_docs = documents[batch_start:batch_end]
                batch_metas = metadatas[batch_start:batch_end]
                batch_ids = ids[batch_start:batch_end]

                logger.info(f"Processing batch {batch_start//batch_size + 1}/{(total_docs + batch_size - 1)//batch_size} ({len(batch_docs)} docs)")

                # Generate dense embeddings for batch
                embeddings = self.embedding_function(batch_docs)

                # Generate sparse embeddings if hybrid search is enabled
                sparse_embeddings = None
                if self.enable_hybrid_search and self.sparse_embedding:
                    # Fit BM25 on documents if not already fitted
                    if not self.sparse_embedding.fitted:
                        self.sparse_embedding.fit(batch_docs)
                    sparse_embeddings = self.sparse_embedding.encode(batch_docs)

                # Create points for Qdrant
                points = []
                for i, (doc_id, embedding, metadata) in enumerate(zip(batch_ids, embeddings, batch_metas)):
                    # Add document text to metadata
                    payload = dict(metadata)
                    payload["document"] = batch_docs[i]

                    # Store the original Zotero key in payload for retrieval
                    payload["item_key"] = doc_id

                    # Convert Zotero key to UUID for Qdrant ID
                    # Use UUID5 with a namespace to create deterministic UUIDs from keys
                    point_id = str(uuid.uuid5(uuid.NAMESPACE_DNS, f"zotero.{doc_id}"))

                    if self.enable_hybrid_search and sparse_embeddings:
                        # Hybrid mode: use named vectors
                        points.append(PointStruct(
                            id=point_id,
                            vector={
                                "dense": embedding,
                                "sparse": sparse_embeddings[i]
                            },
                            payload=payload
                        ))
                    else:
                        # Dense-only mode
                        points.append(PointStruct(
                            id=point_id,
                            vector=embedding,
                            payload=payload
                        ))

                # Upload batch to Qdrant
                self.client.upsert(
                    collection_name=self.collection_name,
                    points=points
                )
                logger.info(f"Uploaded batch {batch_start//batch_size + 1} ({len(points)} points) to Qdrant")

            logger.info(f"Added {total_docs} total documents to Qdrant collection ({mode} mode)")

        except Exception as e:
            logger.error(f"Error adding documents to Qdrant: {e}")
            raise

    def upsert_documents(self,
                        documents: List[str],
                        metadatas: List[Dict[str, Any]],
                        ids: List[str]) -> None:
        """
        Upsert (update or insert) documents to the collection.

        Args:
            documents: List of document texts to embed
            metadatas: List of metadata dictionaries for each document
            ids: List of unique IDs for each document
        """
        # In Qdrant, upsert is the same as add
        self.add_documents(documents, metadatas, ids)

    def search(self,
               query_texts: List[str],
               n_results: int = 10,
               where: Optional[Dict[str, Any]] = None,
               where_document: Optional[Dict[str, Any]] = None,
               use_hybrid: Optional[bool] = None) -> Dict[str, Any]:
        """
        Search for similar documents using hybrid or dense-only search.

        Args:
            query_texts: List of query texts
            n_results: Number of results to return
            where: Metadata filter conditions
            where_document: Document content filter conditions
            use_hybrid: Override to force hybrid or dense search (default: follows enable_hybrid_search)

        Returns:
            Search results in ChromaDB-compatible format
        """
        try:
            # Determine search mode
            hybrid_mode = use_hybrid if use_hybrid is not None else self.enable_hybrid_search

            # Generate query embeddings
            query_embeddings = self.embedding_function(query_texts)

            # Generate sparse embeddings for hybrid search
            query_sparse = None
            if hybrid_mode and self.sparse_embedding:
                query_sparse = self.sparse_embedding.encode(query_texts)

            all_results = {
                "ids": [],
                "distances": [],
                "metadatas": [],
                "documents": []
            }

            for i, query_embedding in enumerate(query_embeddings):
                # Build filter if provided
                query_filter = None
                if where:
                    # Convert ChromaDB-style filter to Qdrant filter
                    query_filter = self._build_filter(where)

                # Search in Qdrant
                if hybrid_mode and query_sparse:
                    # Hybrid search with both dense and sparse vectors
                    from qdrant_client.models import Prefetch, Query

                    search_result = self.client.query_points(
                        collection_name=self.collection_name,
                        prefetch=[
                            Prefetch(
                                query=query_embedding,
                                using="dense",
                                limit=n_results * 2  # Over-fetch for better fusion
                            ),
                            Prefetch(
                                query=query_sparse[i],
                                using="sparse",
                                limit=n_results * 2
                            )
                        ],
                        query=Query(fusion="dbsf"),  # Distribution-Based Score Fusion
                        limit=n_results,
                        query_filter=query_filter
                    ).points
                else:
                    # Dense-only search
                    if self.enable_hybrid_search:
                        # Collection has named vectors, use "dense"
                        search_result = self.client.search(
                            collection_name=self.collection_name,
                            query_vector=("dense", query_embedding),
                            limit=n_results,
                            query_filter=query_filter
                        )
                    else:
                        # Collection has single vector
                        search_result = self.client.search(
                            collection_name=self.collection_name,
                            query_vector=query_embedding,
                            limit=n_results,
                            query_filter=query_filter
                        )

                # Convert to ChromaDB-compatible format
                ids = [str(hit.id) for hit in search_result]
                distances = [1 - hit.score for hit in search_result]  # Convert similarity to distance
                metadatas = []
                documents = []

                for hit in search_result:
                    payload = dict(hit.payload)
                    document = payload.pop("document", "")
                    metadatas.append(payload)
                    documents.append(document)

                # Apply reranking if enabled
                if self.enable_reranking and self.reranker and len(documents) > 0:
                    # Create query-document pairs
                    query_text = query_texts[i]
                    pairs = [[query_text, doc] for doc in documents]

                    # Get reranking scores
                    rerank_scores = self.reranker.predict(pairs)

                    # Sort by reranking scores (higher is better)
                    sorted_indices = sorted(range(len(rerank_scores)),
                                          key=lambda idx: rerank_scores[idx],
                                          reverse=True)

                    # Reorder results
                    ids = [ids[idx] for idx in sorted_indices]
                    distances = [distances[idx] for idx in sorted_indices]
                    metadatas = [metadatas[idx] for idx in sorted_indices]
                    documents = [documents[idx] for idx in sorted_indices]

                    logger.debug(f"Reranked {len(documents)} results using cross-encoder")

                all_results["ids"].append(ids)
                all_results["distances"].append(distances)
                all_results["metadatas"].append(metadatas)
                all_results["documents"].append(documents)

            mode = "hybrid" if hybrid_mode else "dense"
            rerank_status = " + reranking" if self.enable_reranking else ""
            logger.info(f"Semantic search ({mode}{rerank_status}) returned {len(all_results['ids'][0]) if all_results['ids'] else 0} results")
            return all_results
        except Exception as e:
            logger.error(f"Error performing semantic search: {e}")
            raise

    def _build_filter(self, where: Dict[str, Any]) -> Filter:
        """Convert ChromaDB-style filter to Qdrant filter."""
        # Simple conversion for basic equality filters
        # This can be extended for more complex filters
        conditions = []
        for key, value in where.items():
            conditions.append(
                FieldCondition(
                    key=key,
                    match=MatchValue(value=value)
                )
            )
        return Filter(must=conditions) if conditions else None

    def delete_documents(self, ids: List[str]) -> None:
        """
        Delete documents from the collection.

        Args:
            ids: List of document IDs to delete
        """
        try:
            self.client.delete(
                collection_name=self.collection_name,
                points_selector=ids
            )
            logger.info(f"Deleted {len(ids)} documents from Qdrant collection")
        except Exception as e:
            logger.error(f"Error deleting documents from Qdrant: {e}")
            raise

    def get_collection_info(self) -> Dict[str, Any]:
        """Get information about the collection."""
        try:
            collection_info = self.client.get_collection(self.collection_name)
            return {
                "name": self.collection_name,
                "count": collection_info.points_count,
                "embedding_model": self.embedding_model,
                "vector_size": collection_info.config.params.vectors.size
            }
        except Exception as e:
            logger.error(f"Error getting collection info: {e}")
            return {
                "name": self.collection_name,
                "count": 0,
                "embedding_model": self.embedding_model,
                "error": str(e)
            }

    def reset_collection(self) -> None:
        """Reset (clear) the collection."""
        try:
            # Delete and recreate collection
            self.client.delete_collection(collection_name=self.collection_name)

            vector_size = self.embedding_function.get_dimension()

            if self.enable_hybrid_search:
                # Create collection with both dense and sparse vectors
                self.client.create_collection(
                    collection_name=self.collection_name,
                    vectors_config={
                        "dense": VectorParams(
                            size=vector_size,
                            distance=Distance.COSINE
                        )
                    },
                    sparse_vectors_config={
                        "sparse": SparseVectorParams(
                            index=SparseIndexParams()
                        )
                    }
                )
                # Reset BM25 fitted state
                if self.sparse_embedding:
                    self.sparse_embedding.fitted = False
                logger.info(f"Reset hybrid Qdrant collection '{self.collection_name}'")
            else:
                # Create collection with only dense vectors
                self.client.create_collection(
                    collection_name=self.collection_name,
                    vectors_config=VectorParams(
                        size=vector_size,
                        distance=Distance.COSINE
                    )
                )
                logger.info(f"Reset Qdrant collection '{self.collection_name}'")
        except Exception as e:
            logger.error(f"Error resetting collection: {e}")
            raise

    def document_exists(self, doc_id: str) -> bool:
        """
        Check if a document exists in the collection.

        Args:
            doc_id: Zotero item key (will be converted to UUID for lookup)
        """
        try:
            # Convert Zotero key to UUID (same as in add_documents)
            point_id = str(uuid.uuid5(uuid.NAMESPACE_DNS, f"zotero.{doc_id}"))
            result = self.client.retrieve(
                collection_name=self.collection_name,
                ids=[point_id]
            )
            return len(result) > 0
        except Exception:
            return False


def create_qdrant_client(config_path: Optional[str] = None) -> QdrantClientWrapper:
    """
    Create a QdrantClientWrapper instance from configuration.

    Args:
        config_path: Path to configuration file

    Returns:
        Configured QdrantClientWrapper instance
    """
    # Default configuration
    config = {
        "collection_name": "zotero_library",
        "qdrant_url": "http://localhost:6333",
        "qdrant_api_key": None,
        "embedding_model": "default",
        "embedding_config": {}
    }

    # Load configuration from file if it exists
    if config_path and os.path.exists(config_path):
        try:
            with open(config_path, 'r') as f:
                file_config = json.load(f)
                config.update(file_config.get("semantic_search", {}))
        except Exception as e:
            logger.warning(f"Error loading config from {config_path}: {e}")

    # Load configuration from environment variables
    env_embedding_model = os.getenv("ZOTERO_EMBEDDING_MODEL")
    if env_embedding_model:
        config["embedding_model"] = env_embedding_model

    qdrant_url = os.getenv("QDRANT_URL")
    if qdrant_url:
        config["qdrant_url"] = qdrant_url

    qdrant_api_key = os.getenv("QDRANT_API_KEY")
    if qdrant_api_key:
        config["qdrant_api_key"] = qdrant_api_key

    # Set up embedding config from environment
    if config["embedding_model"] == "openai":
        openai_api_key = os.getenv("OPENAI_API_KEY")
        openai_model = os.getenv("OPENAI_EMBEDDING_MODEL", "text-embedding-3-small")
        if openai_api_key:
            config["embedding_config"] = {
                "api_key": openai_api_key,
                "model_name": openai_model
            }

    elif config["embedding_model"] == "gemini":
        gemini_api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
        gemini_model = os.getenv("GEMINI_EMBEDDING_MODEL", "models/text-embedding-004")
        if gemini_api_key:
            config["embedding_config"] = {
                "api_key": gemini_api_key,
                "model_name": gemini_model
            }

    # Get optimization configurations
    enable_hybrid = config.get("enable_hybrid_search", True)
    enable_quantization = config.get("enable_quantization", True)
    hnsw_m = config.get("hnsw_m", 32)
    hnsw_ef_construct = config.get("hnsw_ef_construct", 200)
    enable_reranking = config.get("enable_reranking", True)

    return QdrantClientWrapper(
        collection_name=config["collection_name"],
        qdrant_url=config["qdrant_url"],
        qdrant_api_key=config["qdrant_api_key"],
        embedding_model=config["embedding_model"],
        embedding_config=config["embedding_config"],
        enable_hybrid_search=enable_hybrid,
        enable_quantization=enable_quantization,
        hnsw_m=hnsw_m,
        hnsw_ef_construct=hnsw_ef_construct,
        enable_reranking=enable_reranking
    )
