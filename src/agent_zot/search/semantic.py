"""
Semantic search functionality for Zotero MCP.

This module provides semantic search capabilities by integrating Qdrant
with the existing Zotero client to enable vector-based similarity search
over research libraries. Uses Docling for enhanced document parsing.
"""

import json
import os
import sys
import gc
from contextlib import contextmanager
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed

from pyzotero import zotero

from agent_zot.clients.qdrant import QdrantClientWrapper, create_qdrant_client
from agent_zot.parsers.docling import DoclingParser, parse_zotero_attachment
from agent_zot.clients.neo4j_graphrag import Neo4jGraphRAGClient, create_neo4j_graphrag_client
from agent_zot.clients.zotero import get_zotero_client
from agent_zot.utils.common import format_creators, is_local_mode
from agent_zot.database.local_zotero import LocalZoteroReader, get_local_zotero_reader

logger = logging.getLogger(__name__)


# REMOVED: BoundedThreadPoolExecutor class due to inherent semaphore leak issues
# with callback-based approach. Callbacks don't fire reliably when C++ exceptions
# occur (pypdfium2 AssertionErrors), causing resource_tracker warnings and crashes.
#
# Solution: Use standard ThreadPoolExecutor with as_completed() instead of callbacks.
# This processes results as they complete naturally without relying on callbacks.


@contextmanager
def suppress_stdout():
    """Context manager to suppress stdout temporarily."""
    with open(os.devnull, 'w') as devnull:
        old_stdout = sys.stdout
        sys.stdout = devnull
        try:
            yield
        finally:
            sys.stdout = old_stdout


class ZoteroSemanticSearch:
    """Semantic search interface for Zotero libraries using Qdrant and Docling."""

    def __init__(self,
                 qdrant_client: Optional[QdrantClientWrapper] = None,
                 neo4j_client: Optional[Neo4jGraphRAGClient] = None,
                 config_path: Optional[str] = None):
        """
        Initialize semantic search.

        Args:
            qdrant_client: Optional QdrantClientWrapper instance
            neo4j_client: Optional Neo4jGraphRAGClient instance
            config_path: Path to configuration file
        """
        self.qdrant_client = qdrant_client or create_qdrant_client(config_path)
        self.neo4j_client = neo4j_client or create_neo4j_graphrag_client(config_path)
        self.zotero_client = get_zotero_client()
        self.config_path = config_path

        # Load configuration for Docling parser
        docling_config = self._load_docling_config()

        # Initialize Docling parser with HybridChunker and Granite VLM support
        self.docling_parser = DoclingParser(
            tokenizer=docling_config.get("tokenizer", "sentence-transformers/all-MiniLM-L6-v2"),
            max_tokens=docling_config.get("max_tokens"),
            merge_peers=docling_config.get("merge_peers", True),
            num_threads=docling_config.get("num_threads", 10),
            do_formula_enrichment=docling_config.get("do_formula_enrichment", True),
            do_table_structure=docling_config.get("parse_tables", True),
            enable_ocr_fallback=docling_config.get("ocr", {}).get("fallback_enabled", False),
            ocr_min_text_threshold=docling_config.get("ocr", {}).get("min_text_threshold", 100),
            enable_granite_fallback=docling_config.get("granite_fallback_enabled", False),
            granite_min_text_threshold=docling_config.get("granite_min_text_threshold", 100)
        )

        # Load update configuration
        self.update_config = self._load_update_config()

        # Log Neo4j status
        if self.neo4j_client:
            logger.info("Neo4j GraphRAG integration enabled")
        else:
            logger.info("Neo4j GraphRAG integration disabled")
    
    def _load_docling_config(self) -> Dict[str, Any]:
        """Load Docling chunking configuration from file or use defaults."""
        config = {
            "tokenizer": "sentence-transformers/all-MiniLM-L6-v2",
            "max_tokens": 512,  # Good balance for embeddings
            "merge_peers": True,
            "num_threads": 10,  # Optimized for 10-core CPU
            "do_formula_enrichment": True,  # Convert LaTeX formulas to text
            "parse_tables": True,
            "parse_figures": True,
            "ocr": {
                "enabled": True,
                "conditional": True,
                "min_text_threshold": 100
            }
        }

        if self.config_path and os.path.exists(self.config_path):
            try:
                with open(self.config_path, 'r') as f:
                    file_config = json.load(f)
                    config.update(file_config.get("semantic_search", {}).get("docling", {}))
            except Exception as e:
                logger.warning(f"Error loading Docling config: {e}")

        return config

    def _load_update_config(self) -> Dict[str, Any]:
        """Load update configuration from file or use defaults."""
        config = {
            "auto_update": False,
            "update_frequency": "manual",
            "last_update": None,
            "update_days": 7
        }

        if self.config_path and os.path.exists(self.config_path):
            try:
                with open(self.config_path, 'r') as f:
                    file_config = json.load(f)
                    config.update(file_config.get("semantic_search", {}).get("update_config", {}))
            except Exception as e:
                logger.warning(f"Error loading update config: {e}")

        return config
    
    def _save_update_config(self) -> None:
        """Save update configuration to file."""
        if not self.config_path:
            return
        
        config_dir = Path(self.config_path).parent
        config_dir.mkdir(parents=True, exist_ok=True)
        
        # Load existing config or create new one
        full_config = {}
        if os.path.exists(self.config_path):
            try:
                with open(self.config_path, 'r') as f:
                    full_config = json.load(f)
            except Exception:
                pass
        
        # Update semantic search config
        if "semantic_search" not in full_config:
            full_config["semantic_search"] = {}
        
        full_config["semantic_search"]["update_config"] = self.update_config
        
        try:
            with open(self.config_path, 'w') as f:
                json.dump(full_config, f, indent=2)
        except Exception as e:
            logger.error(f"Error saving update config: {e}")
    
    def _create_document_text(self, item: Dict[str, Any]) -> str:
        """
        Create searchable text from a Zotero item.
        
        Args:
            item: Zotero item dictionary
            
        Returns:
            Combined text for embedding
        """
        data = item.get("data", {})
        
        # Extract key fields for semantic search
        title = data.get("title", "")
        abstract = data.get("abstractNote", "")
        
        # Format creators as text
        creators = data.get("creators", [])
        creators_text = format_creators(creators)
        
        # Additional searchable content
        extra_fields = []
        
        # Publication details
        if publication := data.get("publicationTitle"):
            extra_fields.append(publication)
        
        # Tags
        if tags := data.get("tags"):
            tag_text = " ".join([tag.get("tag", "") for tag in tags])
            extra_fields.append(tag_text)
        
        # Note content (if available)
        if note := data.get("note"):
            # Clean HTML from notes
            import re
            note_text = re.sub(r'<[^>]+>', '', note)
            extra_fields.append(note_text)

        # Full-text content (if available) - MOST IMPORTANT for semantic search
        if fulltext := data.get("fulltext"):
            extra_fields.append(fulltext)

        # Combine all text fields
        text_parts = [title, creators_text, abstract] + extra_fields
        return " ".join(filter(None, text_parts))
    
    def _create_metadata(self, item: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create metadata for a Zotero item.

        Args:
            item: Zotero item dictionary

        Returns:
            Metadata dictionary for Qdrant
        """
        data = item.get("data", {})

        metadata = {
            "item_key": item.get("key", ""),
            "item_type": data.get("itemType", ""),
            "title": data.get("title", ""),
            "date": data.get("date", ""),
            "date_added": data.get("dateAdded", ""),
            "date_modified": data.get("dateModified", ""),
            "creators": format_creators(data.get("creators", [])),
            "publication": data.get("publicationTitle", ""),
            "url": data.get("url", ""),
            "doi": data.get("DOI", ""),

            # Enhanced metadata for advanced filtering
            "journal": data.get("publicationTitle", ""),  # Alias for easier filtering
            "abstract": data.get("abstractNote", ""),
            "volume": data.get("volume", ""),
            "issue": data.get("issue", ""),
            "pages": data.get("pages", ""),
        }
        # If local fulltext field exists, add markers so we can filter later
        if data.get("fulltext"):
            metadata["has_fulltext"] = True
            if data.get("fulltextSource"):
                metadata["fulltext_source"] = data.get("fulltextSource")

        # Add tags as a single string
        if tags := data.get("tags"):
            metadata["tags"] = " ".join([tag.get("tag", "") for tag in tags])
        else:
            metadata["tags"] = ""

        # Add citation key if available
        extra = data.get("extra", "")
        citation_key = ""
        for line in extra.split("\n"):
            if line.lower().startswith(("citation key:", "citationkey:")):
                citation_key = line.split(":", 1)[1].strip()
                break
        metadata["citation_key"] = citation_key

        return metadata
    
    def should_update_database(self) -> bool:
        """Check if the database should be updated based on configuration."""
        if not self.update_config.get("auto_update", False):
            return False
        
        frequency = self.update_config.get("update_frequency", "manual")
        
        if frequency == "manual":
            return False
        elif frequency == "startup":
            return True
        elif frequency == "daily":
            last_update = self.update_config.get("last_update")
            if not last_update:
                return True
            
            last_update_date = datetime.fromisoformat(last_update)
            return datetime.now() - last_update_date >= timedelta(days=1)
        elif frequency.startswith("every_"):
            try:
                days = int(frequency.split("_")[1])
                last_update = self.update_config.get("last_update")
                if not last_update:
                    return True
                
                last_update_date = datetime.fromisoformat(last_update)
                return datetime.now() - last_update_date >= timedelta(days=days)
            except (ValueError, IndexError):
                return False
        
        return False
    
    def _get_items_from_source(self, limit: Optional[int] = None, extract_fulltext: bool = False) -> List[Dict[str, Any]]:
        """
        Get items from either local database or API.
        
        Uses local database only when both extract_fulltext=True and is_local_mode().
        Otherwise uses API (faster, metadata-only).
        
        Args:
            limit: Optional limit on number of items
            extract_fulltext: Whether to extract fulltext content
            
        Returns:
            List of items in API-compatible format
        """
        if extract_fulltext and is_local_mode():
            return self._get_items_from_local_db(limit, extract_fulltext=extract_fulltext)
        else:
            return self._get_items_from_api(limit)
    
    def _get_item_metadata_list(self, limit: Optional[int] = None) -> List[Any]:
        """
        Get lightweight metadata list of items from local database.
        Fast operation - returns NamedTuple objects without fulltext extraction.

        Args:
            limit: Optional limit on number of items

        Returns:
            List of NamedTuple items (without fulltext)
        """
        logger.info("Fetching item metadata from local Zotero database...")

        try:
            pdf_max_pages = None
            try:
                if self.config_path and os.path.exists(self.config_path):
                    with open(self.config_path, 'r') as _f:
                        _cfg = json.load(_f)
                        pdf_max_pages = _cfg.get('semantic_search', {}).get('extraction', {}).get('pdf_max_pages')
            except Exception:
                pass

            with suppress_stdout(), LocalZoteroReader(pdf_max_pages=pdf_max_pages) as reader:
                # Fetch metadata only (fast)
                sys.stderr.write("Scanning local Zotero database for items...\n")
                local_items = reader.get_items_with_text(limit=limit, include_fulltext=False)
                candidate_count = len(local_items)
                sys.stderr.write(f"Found {candidate_count} candidate items.\n")

                # Deduplication logic (prefer journalArticle over preprint)
                def norm(s: Optional[str]) -> Optional[str]:
                    if not s:
                        return None
                    return "".join(s.lower().split())

                key_to_best = {}
                for it in local_items:
                    doi_key = ("doi", norm(getattr(it, "doi", None))) if getattr(it, "doi", None) else None
                    title_key = ("title", norm(getattr(it, "title", None))) if getattr(it, "title", None) else None

                    def consider(k):
                        if not k:
                            return
                        cur = key_to_best.get(k)
                        if cur is None:
                            key_to_best[k] = it
                        else:
                            prefer_types = {"journalArticle": 2, "preprint": 1}
                            cur_score = prefer_types.get(getattr(cur, "item_type", ""), 0)
                            new_score = prefer_types.get(getattr(it, "item_type", ""), 0)
                            if new_score > cur_score:
                                key_to_best[k] = it

                    consider(doi_key)
                    consider(title_key)

                # Filter out preprints that have journalArticle alternatives
                filtered_items = []
                for it in local_items:
                    if getattr(it, "item_type", None) == "preprint":
                        k_doi = ("doi", norm(getattr(it, "doi", None))) if getattr(it, "doi", None) else None
                        k_title = ("title", norm(getattr(it, "title", None))) if getattr(it, "title", None) else None
                        drop = False
                        for k in (k_doi, k_title):
                            if not k:
                                continue
                            best = key_to_best.get(k)
                            if best is not None and best is not it and getattr(best, "item_type", None) == "journalArticle":
                                drop = True
                                break
                        if drop:
                            continue
                    filtered_items.append(it)

                total_items = len(filtered_items)
                if total_items != candidate_count:
                    sys.stderr.write(f"After filtering/dedup: {total_items} items to process.\n")

                logger.info(f"Retrieved {total_items} item metadata records from local database")
                return filtered_items

        except Exception as e:
            logger.error(f"Error reading from local database: {e}")
            raise

    def _extract_batch_fulltext(self, items: List[Any]) -> List[Dict[str, Any]]:
        """
        Extract fulltext for a batch of items and convert to API-compatible format.
        Uses parallel extraction with 8 workers (optimized for M1 Pro).

        Args:
            items: List of NamedTuple items (metadata only)

        Returns:
            List of API-compatible items with fulltext extracted
        """
        if not items:
            return []

        logger.info(f"Extracting fulltext for batch of {len(items)} items...")

        # Parallel fulltext extraction
        max_workers = 8
        extraction_data = {}  # item_key -> {"fulltext": ..., "chunks": ..., "source": ..., "metadata": ...}

        def extract_item_fulltext(it):
            """Extract fulltext for a single item (thread-safe). Returns (item_key, extraction_dict)."""
            item_key = it.key
            extraction_result = {"fulltext": "", "chunks": [], "source": "", "metadata": {}}

            try:
                # Create thread-local reader to avoid SQLite threading issues
                from agent_zot.database.local_zotero import LocalZoteroReader
                thread_reader = LocalZoteroReader()
                result = thread_reader.extract_fulltext_for_item(it.item_id)

                if result:
                    # Check if tuple format first
                    if isinstance(result, tuple) and len(result) == 2:
                        data, source = result
                        # Tuple can contain (dict, source) or (string, source)
                        if isinstance(data, dict) and "chunks" in data:
                            # New Docling format: (dict_with_chunks, "docling")
                            extraction_result["chunks"] = data["chunks"]
                            extraction_result["fulltext"] = data.get("text", "")
                            extraction_result["source"] = source
                            extraction_result["metadata"] = data.get("metadata", {})
                        else:
                            # Legacy format: (text_string, source)
                            extraction_result["fulltext"] = data if isinstance(data, str) else str(data)
                            extraction_result["source"] = source
                    # Plain dict format (without tuple wrapper)
                    elif isinstance(result, dict) and "chunks" in result:
                        extraction_result["chunks"] = result["chunks"]
                        extraction_result["fulltext"] = result.get("text", "")
                        extraction_result["source"] = "docling"
                        extraction_result["metadata"] = result.get("metadata", {})
                    # Plain string format
                    else:
                        extraction_result["fulltext"] = result
                        extraction_result["source"] = "pdfminer"
            except Exception as e:
                logger.error(f"Error extracting fulltext for item {it.item_id}: {e}")

            return (item_key, extraction_result)

        # Extract in parallel
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_item = {executor.submit(extract_item_fulltext, it): it for it in items}

            for future in as_completed(future_to_item):
                try:
                    item_key, extraction_result = future.result()
                    extraction_data[item_key] = extraction_result
                except Exception as e:
                    logger.error(f"Error extracting fulltext: {e}")

        # Convert to API-compatible format
        api_items = []
        for item in items:
            item_extraction = extraction_data.get(item.key, {"fulltext": "", "chunks": [], "source": "", "metadata": {}})

            api_item = {
                "key": item.key,
                "version": 0,
                "data": {
                    "key": item.key,
                    "itemType": getattr(item, 'item_type', None) or "journalArticle",
                    "title": item.title or "",
                    "abstractNote": item.abstract or "",
                    "extra": item.extra or "",
                    "fulltext": item_extraction["fulltext"],
                    "fulltextSource": item_extraction["source"],
                    "chunks": item_extraction["chunks"],
                    "docling_metadata": item_extraction["metadata"],
                    "dateAdded": item.date_added,
                    "dateModified": item.date_modified,
                    "creators": self._parse_creators_string(item.creators) if item.creators else []
                }
            }

            if item.notes:
                api_item["data"]["notes"] = item.notes

            api_items.append(api_item)

        logger.info(f"Extracted fulltext for {len(api_items)} items")
        return api_items

    def _get_items_from_local_db(self, limit: Optional[int] = None, extract_fulltext: bool = False) -> List[Dict[str, Any]]:
        """
        Get items from local Zotero database.

        Args:
            limit: Optional limit on number of items
            extract_fulltext: Whether to extract fulltext content

        Returns:
            List of items in API-compatible format
        """
        logger.info("Fetching items from local Zotero database...")
        
        try:
            # Load per-run config, including extraction limits if provided
            pdf_max_pages = None
            # If semantic_search config file exists, prefer its setting
            try:
                if self.config_path and os.path.exists(self.config_path):
                    with open(self.config_path, 'r') as _f:
                        _cfg = json.load(_f)
                        pdf_max_pages = _cfg.get('semantic_search', {}).get('extraction', {}).get('pdf_max_pages')
            except Exception:
                pass

            with suppress_stdout(), LocalZoteroReader(pdf_max_pages=pdf_max_pages) as reader:
                # Phase 1: fetch metadata only (fast)
                sys.stderr.write("Scanning local Zotero database for items...\n")
                local_items = reader.get_items_with_text(limit=limit, include_fulltext=False)
                candidate_count = len(local_items)
                sys.stderr.write(f"Found {candidate_count} candidate items.\n")

                # Optional deduplication: if preprint and journalArticle share a DOI/title, keep journalArticle
                # Build index by (normalized DOI or normalized title)
                def norm(s: Optional[str]) -> Optional[str]:
                    if not s:
                        return None
                    return "".join(s.lower().split())

                key_to_best = {}
                for it in local_items:
                    doi_key = ("doi", norm(getattr(it, "doi", None))) if getattr(it, "doi", None) else None
                    title_key = ("title", norm(getattr(it, "title", None))) if getattr(it, "title", None) else None

                    def consider(k):
                        if not k:
                            return
                        cur = key_to_best.get(k)
                        # Prefer journalArticle over preprint; otherwise keep first
                        if cur is None:
                            key_to_best[k] = it
                        else:
                            prefer_types = {"journalArticle": 2, "preprint": 1}
                            cur_score = prefer_types.get(getattr(cur, "item_type", ""), 0)
                            new_score = prefer_types.get(getattr(it, "item_type", ""), 0)
                            if new_score > cur_score:
                                key_to_best[k] = it

                    consider(doi_key)
                    consider(title_key)

                # If a preprint loses against a journal article for same DOI/title, drop it
                filtered_items = []
                for it in local_items:
                    # If there is a journalArticle alternative for same DOI or title, and this is preprint, drop
                    if getattr(it, "item_type", None) == "preprint":
                        k_doi = ("doi", norm(getattr(it, "doi", None))) if getattr(it, "doi", None) else None
                        k_title = ("title", norm(getattr(it, "title", None))) if getattr(it, "title", None) else None
                        drop = False
                        for k in (k_doi, k_title):
                            if not k:
                                continue
                            best = key_to_best.get(k)
                            if best is not None and best is not it and getattr(best, "item_type", None) == "journalArticle":
                                drop = True
                                break
                        if drop:
                            continue
                    filtered_items.append(it)

                local_items = filtered_items
                total_to_extract = len(local_items)
                if total_to_extract != candidate_count:
                    try:
                        sys.stderr.write(f"After filtering/dedup: {total_to_extract} items to process. Extracting content...\n")
                    except Exception:
                        pass
                else:
                    try:
                        sys.stderr.write("Extracting content...\n")
                    except Exception:
                        pass

                # Phase 2: selectively extract fulltext only when requested
                # Store extraction results in dict (NamedTuples are immutable!)
                extraction_data = {}  # item_key -> {"fulltext": ..., "chunks": ..., "source": ..., "metadata": ...}

                if extract_fulltext:
                    # Parallel fulltext extraction with BoundedThreadPoolExecutor
                    # OPTIMIZED FOR M1 PRO (8 performance + 2 efficiency cores):
                    # - 8 workers uses all 8 performance cores (14% faster than 7 workers)
                    # - 2 efficiency cores handle system tasks, keeping UI responsive
                    # - BoundedSemaphore prevents semaphore leak by limiting queue size to 2x workers (16)
                    # - Each worker uses 2 Docling threads (8 workers × 2 = 16 threads total)
                    max_workers = 8  # INCREASED from 7 to fully utilize 8 performance cores
                    max_queue_size = 16  # 2x workers prevents excessive semaphore accumulation
                    batch_size = 200  # INCREASED from 100: reduces batch overhead, faster overall
                    extracted = 0

                    def extract_item_fulltext(it):
                        """Extract fulltext for a single item (thread-safe). Returns (item_key, extraction_dict)."""
                        item_key = it.key
                        extraction_result = {"fulltext": "", "chunks": [], "source": "", "metadata": {}}

                        try:
                            # Create thread-local reader to avoid SQLite threading issues
                            from agent_zot.database.local_zotero import LocalZoteroReader
                            thread_reader = LocalZoteroReader()
                            result = thread_reader.extract_fulltext_for_item(it.item_id)
                            logger.info(f"[DEBUG] extract_fulltext_for_item returned: type={type(result)}, is_tuple={isinstance(result, tuple)}, len={len(result) if isinstance(result, (tuple, list)) else 'N/A'}")
                            if result:
                                # Check if tuple format first
                                if isinstance(result, tuple) and len(result) == 2:
                                    data, source = result
                                    logger.info(f"[DEBUG] Tuple contents: data_type={type(data)}, is_dict={isinstance(data, dict)}, has_chunks={'chunks' in data if isinstance(data, dict) else False}, source={source}")
                                    # Tuple can contain (dict, source) or (string, source)
                                    if isinstance(data, dict) and "chunks" in data:
                                        # New Docling format: (dict_with_chunks, "docling")
                                        extraction_result["chunks"] = data["chunks"]
                                        extraction_result["fulltext"] = data.get("text", "")
                                        extraction_result["source"] = source
                                        extraction_result["metadata"] = data.get("metadata", {})
                                    else:
                                        # Legacy format: (text_string, source)
                                        extraction_result["fulltext"] = data if isinstance(data, str) else str(data)
                                        extraction_result["source"] = source
                                # Plain dict format (without tuple wrapper)
                                elif isinstance(result, dict) and "chunks" in result:
                                    extraction_result["chunks"] = result["chunks"]
                                    extraction_result["fulltext"] = result.get("text", "")
                                    extraction_result["source"] = "docling"
                                    extraction_result["metadata"] = result.get("metadata", {})
                                # Plain string format
                                else:
                                    extraction_result["fulltext"] = result
                                    extraction_result["source"] = "pdfminer"
                        except Exception as e:
                            logger.error(f"Error extracting fulltext for item {it.item_id}: {e}")

                        return (item_key, extraction_result)

                    # Process in batches to prevent semaphore accumulation
                    for batch_start in range(0, len(local_items), batch_size):
                        batch_end = min(batch_start + batch_size, len(local_items))
                        batch_items = local_items[batch_start:batch_end]

                        logger.info(f"Processing batch {batch_start}-{batch_end} ({len(batch_items)} items) with {max_workers} workers")

                        # Use standard ThreadPoolExecutor with as_completed()
                        # FIXED: Removed BoundedSemaphore approach due to callback reliability issues
                        # with C++ exceptions from pypdfium2. as_completed() naturally limits memory
                        # by processing results as they complete without relying on callbacks.
                        with ThreadPoolExecutor(max_workers=max_workers) as executor:
                            # Submit all extraction tasks for this batch
                            future_to_item = {executor.submit(extract_item_fulltext, it): it for it in batch_items}

                            # Process results as they complete (natural backpressure)
                            for future in as_completed(future_to_item):
                                try:
                                    # Get the result (item_key, extraction_dict)
                                    item_key, extraction_result = future.result()
                                    extraction_data[item_key] = extraction_result
                                    extracted += 1
                                    if extracted % 25 == 0 and total_to_extract:
                                        try:
                                            sys.stderr.write(f"Extracted content for {extracted}/{total_to_extract} items (parallel with {max_workers} workers)...\n")
                                        except Exception:
                                            pass
                                except Exception as e:
                                    logger.error(f"Error extracting fulltext: {e}")

                        # Explicit cleanup after each batch
                        gc.collect()
                        logger.info(f"Batch {batch_start}-{batch_end} complete, garbage collected")
                
                # Convert to API-compatible format
                api_items = []
                for item in local_items:
                    # Get extraction data for this item (if available)
                    item_extraction = extraction_data.get(item.key, {"fulltext": "", "chunks": [], "source": "", "metadata": {}})

                    # DEBUG: Log chunk data flow
                    logger.info(f"[DEBUG] Item {item.key}: chunks in extraction_data: {len(item_extraction['chunks'])}")

                    # Create API-compatible item structure
                    api_item = {
                        "key": item.key,
                        "version": 0,  # Local items don't have versions
                        "data": {
                            "key": item.key,
                            "itemType": getattr(item, 'item_type', None) or "journalArticle",
                            "title": item.title or "",
                            "abstractNote": item.abstract or "",
                            "extra": item.extra or "",
                            # Include fulltext from extraction_data dict (not from NamedTuple which is immutable)
                            "fulltext": item_extraction["fulltext"] if extract_fulltext else "",
                            "fulltextSource": item_extraction["source"] if extract_fulltext else "",
                            # Include Docling chunks from extraction_data dict
                            "chunks": item_extraction["chunks"] if extract_fulltext else [],
                            "docling_metadata": item_extraction["metadata"] if extract_fulltext else {},
                            "dateAdded": item.date_added,
                            "dateModified": item.date_modified,
                            "creators": self._parse_creators_string(item.creators) if item.creators else []
                        }
                    }

                    # Add notes if available
                    if item.notes:
                        api_item["data"]["notes"] = item.notes

                    # DEBUG: Log what's in the API item
                    logger.info(f"[DEBUG] Item {item.key}: chunks in API data: {len(api_item['data']['chunks'])}")

                    api_items.append(api_item)
                
                logger.info(f"Retrieved {len(api_items)} items from local database")
                return api_items
                
        except Exception as e:
            logger.error(f"Error reading from local database: {e}")
            logger.info("Falling back to API...")
            return self._get_items_from_api(limit)
    
    def _parse_creators_string(self, creators_str: str) -> List[Dict[str, str]]:
        """
        Parse creators string from local DB into API format.
        
        Args:
            creators_str: String like "Smith, John; Doe, Jane"
            
        Returns:
            List of creator objects
        """
        if not creators_str:
            return []
        
        creators = []
        for creator in creators_str.split(';'):
            creator = creator.strip()
            if not creator:
                continue
                
            if ',' in creator:
                last, first = creator.split(',', 1)
                creators.append({
                    "creatorType": "author",
                    "firstName": first.strip(),
                    "lastName": last.strip()
                })
            else:
                creators.append({
                    "creatorType": "author", 
                    "name": creator
                })
        
        return creators
    
    def _get_items_from_api(self, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Get items from Zotero API (original implementation).
        
        Args:
            limit: Optional limit on number of items
            
        Returns:
            List of items from API
        """
        logger.info("Fetching items from Zotero API...")
        
        # Fetch items in batches to handle large libraries
        batch_size = 100
        start = 0
        all_items = []
        
        while True:
            batch_params = {"start": start, "limit": batch_size}
            if limit and len(all_items) >= limit:
                break
            
            try:
                items = self.zotero_client.items(**batch_params)
            except Exception as e:
                if "Connection refused" in str(e):
                    error_msg = (
                        "Cannot connect to Zotero local API. Please ensure:\n"
                        "1. Zotero is running\n"
                        "2. Local API is enabled in Zotero Preferences > Advanced > Enable HTTP server\n"
                        "3. The local API port (default 23119) is not blocked"
                    )
                    raise Exception(error_msg) from e
                else:
                    raise Exception(f"Zotero API connection error: {e}") from e
            if not items:
                break
            
            # Filter out attachments and notes by default
            filtered_items = [
                item for item in items 
                if item.get("data", {}).get("itemType") not in ["attachment", "note"]
            ]
            
            all_items.extend(filtered_items)
            start += batch_size
            
            if len(items) < batch_size:
                break
        
        if limit:
            all_items = all_items[:limit]
        
        logger.info(f"Retrieved {len(all_items)} items from API")
        return all_items
    
    def update_database(self,
                       force_full_rebuild: Optional[bool] = None,
                       limit: Optional[int] = None,
                       extract_fulltext: Optional[bool] = None) -> Dict[str, Any]:
        """
        Update the semantic search database with Zotero items.

        Args:
            force_full_rebuild: Whether to rebuild the entire database (default: read from config)
            limit: Limit number of items to process (for testing)
            extract_fulltext: Whether to extract fulltext content from local database (default: read from config)

        Returns:
            Update statistics
        """
        # Read force_rebuild from config if not explicitly provided
        if force_full_rebuild is None:
            force_full_rebuild = self.update_config.get("force_rebuild", False)
            logger.info(f"Using force_rebuild from config: {force_full_rebuild}")

        # HARDCODED: Always extract fulltext for local mode (agent-zot's primary use case)
        # Can be overridden by explicit CLI flag if needed
        if extract_fulltext is None:
            extract_fulltext = True  # Always extract fulltext by default
            logger.info(f"Using extract_fulltext default: {extract_fulltext} (hardcoded for local mode)")

        logger.info("Starting database update...")
        start_time = datetime.now()
        
        stats = {
            "total_items": 0,
            "processed_items": 0,
            "added_items": 0,
            "updated_items": 0,
            "skipped_items": 0,
            "errors": 0,
            "start_time": start_time.isoformat(),
            "duration": None
        }
        
        try:
            # Reset collection if force rebuild
            if force_full_rebuild:
                logger.info("Force rebuilding database...")
                self.qdrant_client.reset_collection()

            # STREAMING BATCH PROCESSING:
            # Get lightweight metadata list first (fast), then extract/process in streaming batches
            if extract_fulltext and is_local_mode():
                # Get metadata-only list (fast - no fulltext extraction yet)
                metadata_items = self._get_item_metadata_list(limit=limit)
                stats["total_items"] = len(metadata_items)
                logger.info(f"Found {stats['total_items']} items to process in streaming batches")

                try:
                    sys.stderr.write(f"Total items to index: {stats['total_items']}\n")
                    sys.stderr.write("Using STREAMING BATCH mode: extract → embed → Qdrant → Neo4j per batch\n")
                except Exception:
                    pass

                # Process in streaming batches through ENTIRE pipeline
                batch_size = 50
                next_milestone = 10 if stats["total_items"] >= 10 else stats["total_items"]
                seen_items = 0

                for i in range(0, len(metadata_items), batch_size):
                    batch_metadata = metadata_items[i:i + batch_size]
                    logger.info(f"Processing streaming batch {i//batch_size + 1}: items {i+1}-{min(i+batch_size, stats['total_items'])}")

                    # Extract fulltext for THIS batch only (not all items)
                    batch_with_fulltext = self._extract_batch_fulltext(batch_metadata)

                    # Process batch through embedding + Qdrant + Neo4j
                    batch_stats = self._process_item_batch(batch_with_fulltext, force_full_rebuild)

                    stats["processed_items"] += batch_stats["processed"]
                    stats["added_items"] += batch_stats["added"]
                    stats["updated_items"] += batch_stats["updated"]
                    stats["skipped_items"] += batch_stats["skipped"]
                    stats["errors"] += batch_stats["errors"]
                    seen_items += len(batch_metadata)

                    logger.info(f"Batch complete: {seen_items}/{stats['total_items']} items (added: {stats['added_items']}, skipped: {stats['skipped_items']})")

                    # Progress reporting
                    try:
                        while seen_items >= next_milestone and next_milestone > 0:
                            sys.stderr.write(f"Processed: {next_milestone}/{stats['total_items']} added:{stats['added_items']} skipped:{stats['skipped_items']} errors:{stats['errors']}\n")
                            next_milestone += 10
                            if next_milestone > stats["total_items"]:
                                next_milestone = stats["total_items"]
                                break
                    except Exception:
                        pass

                    # Explicit garbage collection after each batch
                    gc.collect()

            else:
                # API mode or no fulltext extraction: use old method (load all at once)
                all_items = self._get_items_from_source(limit=limit, extract_fulltext=extract_fulltext)
                stats["total_items"] = len(all_items)
                logger.info(f"Found {stats['total_items']} items to process")

                try:
                    sys.stderr.write(f"Total items to index: {stats['total_items']}\n")
                except Exception:
                    pass

                # Process items in batches
                batch_size = 50
                next_milestone = 10 if stats["total_items"] >= 10 else stats["total_items"]
                seen_items = 0

                for i in range(0, len(all_items), batch_size):
                    batch = all_items[i:i + batch_size]
                    batch_stats = self._process_item_batch(batch, force_full_rebuild)

                    stats["processed_items"] += batch_stats["processed"]
                    stats["added_items"] += batch_stats["added"]
                    stats["updated_items"] += batch_stats["updated"]
                    stats["skipped_items"] += batch_stats["skipped"]
                    stats["errors"] += batch_stats["errors"]
                    seen_items += len(batch)

                    logger.info(f"Processed {seen_items}/{stats['total_items']} items (added: {stats['added_items']}, skipped: {stats['skipped_items']})")

                    try:
                        while seen_items >= next_milestone and next_milestone > 0:
                            sys.stderr.write(f"Processed: {next_milestone}/{stats['total_items']} added:{stats['added_items']} skipped:{stats['skipped_items']} errors:{stats['errors']}\n")
                            next_milestone += 10
                            if next_milestone > stats["total_items"]:
                                next_milestone = stats["total_items"]
                                break
                    except Exception:
                        pass
            
            # Update last update time
            self.update_config["last_update"] = datetime.now().isoformat()
            self._save_update_config()
            
            end_time = datetime.now()
            stats["duration"] = str(end_time - start_time)
            stats["end_time"] = end_time.isoformat()
            
            logger.info(f"Database update completed in {stats['duration']}")
            return stats
            
        except Exception as e:
            logger.error(f"Error updating database: {e}")
            stats["error"] = str(e)
            end_time = datetime.now()
            stats["duration"] = str(end_time - start_time)
            return stats
    
    def _truncate_text_for_embedding(self, text: str, max_tokens: int = 5000) -> str:
        """
        Truncate text to fit within OpenAI's token limit.

        Uses very conservative estimate: 1 token ≈ 3 characters for safety.
        Default max_tokens=5000 leaves large buffer below 8192 limit.

        Args:
            text: Text to truncate
            max_tokens: Maximum number of tokens (default: 5000)

        Returns:
            Truncated text
        """
        # Very conservative estimate: 1 token ≈ 3 chars (large safety buffer)
        max_chars = int(max_tokens * 3)

        if len(text) <= max_chars:
            return text

        # Truncate and add indicator
        truncated = text[:max_chars]
        logger.debug(f"Truncated text from {len(text)} to {len(truncated)} chars (~{max_tokens} tokens)")
        return truncated

    def _process_item_batch(self, items: List[Dict[str, Any]], force_rebuild: bool = False) -> Dict[str, int]:
        """
        Process a batch of items with chunk-based indexing.

        Deduplication is ALWAYS enabled - skips items/chunks that already exist in Qdrant.
        The force_rebuild parameter is kept for compatibility but no longer affects deduplication.

        If Docling chunks are available, indexes each chunk separately.
        Otherwise falls back to document-level indexing.

        Note: Parallelization happens upstream in _get_items_from_local_db during PDF extraction.
        """
        stats = {"processed": 0, "added": 0, "updated": 0, "skipped": 0, "errors": 0}

        documents = []
        metadatas = []
        ids = []

        for item in items:
            try:
                item_key = item.get("key", "")
                if not item_key:
                    stats["skipped"] += 1
                    continue

                data = item.get("data", {})
                chunks = data.get("chunks", [])

                # DEBUG: Log chunks at indexing stage
                logger.info(f"[DEBUG] Item {item_key}: chunks array length at indexing: {len(chunks)}")

                # CHUNK-BASED INDEXING (new, preferred method)
                if chunks:
                    logger.debug(f"Indexing {len(chunks)} chunks for item {item_key}")

                    # Create base metadata for this document
                    base_metadata = self._create_metadata(item)

                    for chunk in chunks:
                        chunk_id = chunk.get("chunk_id", 0)
                        chunk_text = chunk.get("text", "")
                        chunk_meta = chunk.get("meta", {})

                        if not chunk_text.strip():
                            continue

                        # Create unique ID for this chunk
                        chunk_point_id = f"{item_key}_chunk_{chunk_id}"

                        # ALWAYS check if chunk already exists (deduplication)
                        # force_rebuild only controls collection reset, not per-item checks
                        if self.qdrant_client.document_exists(chunk_point_id):
                            continue

                        # Create metadata for this chunk
                        chunk_metadata = base_metadata.copy()
                        chunk_metadata["parent_item_key"] = item_key
                        chunk_metadata["chunk_id"] = chunk_id
                        chunk_metadata["chunk_headings"] = chunk_meta.get("headings", [])
                        chunk_metadata["is_chunk"] = True

                        # Add Neo4j references for bidirectional linking (GraphRAG integration)
                        chunk_metadata["neo4j_paper_id"] = f"paper:{item_key}"
                        chunk_metadata["neo4j_chunk_id"] = f"chunk:{item_key}_{chunk_id}"

                        documents.append(chunk_text)
                        metadatas.append(chunk_metadata)
                        ids.append(chunk_point_id)

                    stats["processed"] += 1

                # DOCUMENT-LEVEL INDEXING (fallback for items without chunks)
                else:
                    # ALWAYS check if item already exists (deduplication)
                    # force_rebuild only controls collection reset, not per-item checks
                    if self.qdrant_client.document_exists(item_key):
                        stats["skipped"] += 1
                        continue

                    # Create document text from available fields
                    fulltext = data.get("fulltext", "")
                    # Handle case where fulltext might be a dict (from Docling) - extract text field
                    if isinstance(fulltext, dict):
                        fulltext = fulltext.get("text", "")
                    doc_text = fulltext if fulltext and fulltext.strip() else self._create_document_text(item)

                    # Truncate only for document-level indexing (chunks are already sized correctly)
                    doc_text = self._truncate_text_for_embedding(doc_text)

                    metadata = self._create_metadata(item)
                    metadata["is_chunk"] = False  # Mark as document-level

                    # Add Neo4j references for bidirectional linking (GraphRAG integration)
                    metadata["neo4j_paper_id"] = f"paper:{item_key}"

                    if not doc_text.strip():
                        stats["skipped"] += 1
                        continue

                    documents.append(doc_text)
                    metadatas.append(metadata)
                    ids.append(item_key)

                    stats["processed"] += 1

            except Exception as e:
                logger.error(f"Error processing item {item.get('key', 'unknown')}: {e}")
                stats["errors"] += 1

        # Add documents/chunks to Qdrant if any
        if documents:
            try:
                self.qdrant_client.upsert_documents(documents, metadatas, ids)
                stats["added"] += len(documents)

                # Also add to Neo4j knowledge graph if enabled (using batch processing)
                if self.neo4j_client:
                    logger.info(f"Calling Neo4j integration for {len(items)} items...")
                    self._add_items_to_graph(items, documents)
                else:
                    logger.warning("Neo4j client is None - skipping graph extraction")

            except Exception as e:
                logger.error(f"Error adding documents to Qdrant: {e}")
                stats["errors"] += len(documents)

        return stats

    def _add_items_to_graph(self, items: List[Dict[str, Any]], documents: List[str]):
        """
        Add items to Neo4j knowledge graph with chunk-level entity extraction.

        Uses the SAME Docling chunks as Qdrant for consistent representation.
        Creates both Paper nodes and Chunk nodes, with entities linked at chunk level.

        Args:
            items: List of Zotero items with Docling chunks
            documents: Corresponding document texts (for compatibility)

        Note: This implementation follows Qdrant documentation best practices for GraphRAG:
        - Uses identical Docling chunks for both Qdrant and Neo4j
        - Creates chunk-level nodes in Neo4j with bidirectional links to Qdrant
        - Extracts entities per chunk (not per paper) for granular retrieval
        """
        if not self.neo4j_client:
            return

        logger.info(f"[NEO4J DEBUG] _add_items_to_graph: Processing {len(items)} items")

        # Prepare papers with chunk-level data
        papers_with_chunks = []
        for item in items:
            try:
                item_data = item.get("data", {})
                paper_key = item.get("key", "")
                title = item_data.get("title", "Untitled")
                abstract = item_data.get("abstractNote", "")

                # Extract Docling chunks (same as used in Qdrant)
                fulltext_data = item_data.get("fulltext", "")
                docling_chunks = []

                logger.info(f"[NEO4J DEBUG] Item {paper_key}: fulltext_data type = {type(fulltext_data)}")

                if isinstance(fulltext_data, dict):
                    # Docling format: {"text": "...", "chunks": [...]}
                    docling_chunks = fulltext_data.get("chunks", [])
                    logger.info(f"[NEO4J DEBUG] Item {paper_key}: Found {len(docling_chunks)} Docling chunks")

                # Skip if no chunks (fall back to paper-level only)
                if not docling_chunks:
                    logger.info(f"[NEO4J DEBUG] No Docling chunks for {paper_key}, skipping chunk-level extraction")
                    continue

                # Extract authors
                creators = item_data.get("creators", [])
                authors = [f"{c.get('firstName', '')} {c.get('lastName', '')}".strip() for c in creators]

                # Extract year
                year = item_data.get("date", "")
                try:
                    year = int(year[:4]) if year else None
                except Exception:
                    year = None

                # Prepare chunk data with Qdrant point IDs for bidirectional linking
                chunk_data = []
                for chunk in docling_chunks[:20]:  # Limit to first 20 chunks for LLM processing
                    chunk_id = chunk.get("chunk_id", 0)
                    chunk_text = chunk.get("text", "")

                    if not chunk_text.strip():
                        continue

                    # Include metadata for context (headings help entity extraction)
                    chunk_meta = chunk.get("meta", {})
                    headings = chunk_meta.get("headings", [])

                    # Create context-aware chunk representation
                    chunk_context = chunk_text
                    if headings:
                        chunk_context = f"[Section: {' > '.join(headings)}]\n{chunk_text}"

                    chunk_data.append({
                        "chunk_id": chunk_id,
                        "text": chunk_context,
                        "qdrant_point_id": f"{paper_key}_chunk_{chunk_id}",  # Link to Qdrant
                        "headings": headings
                    })

                if chunk_data:
                    logger.info(f"[NEO4J DEBUG] Item {paper_key}: Prepared {len(chunk_data)} chunks for Neo4j")
                    papers_with_chunks.append({
                        "paper_key": paper_key,
                        "title": title,
                        "abstract": abstract,
                        "authors": authors,
                        "year": year,
                        "chunks": chunk_data  # Now contains full chunk objects with metadata
                    })
                else:
                    logger.info(f"[NEO4J DEBUG] Item {paper_key}: No valid chunk_data after processing")

            except Exception as e:
                logger.error(f"Error preparing item {item.get('key', 'unknown')} for graph: {e}")

        logger.info(f"[NEO4J DEBUG] Prepared {len(papers_with_chunks)} papers for Neo4j extraction")

        # Add papers with chunk-level extraction to Neo4j
        if papers_with_chunks:
            try:
                logger.info(f"Extracting chunk-level entities for {len(papers_with_chunks)} papers to Neo4j...")
                result = self.neo4j_client.add_papers_with_chunks(papers_with_chunks, batch_size=5)
                logger.info(f"Neo4j GraphRAG: Added {result.get('successful', 0)} papers with {result.get('total_chunks', 0)} chunks (failed: {result.get('failed', 0)})")
            except Exception as e:
                logger.error(f"Error adding papers with chunks to Neo4j graph: {e}")

    def search(self,
               query: str,
               limit: int = 10,
               filters: Optional[Dict[str, Any]] = None,
               use_hybrid: Optional[bool] = None) -> Dict[str, Any]:
        """
        Perform semantic search over the Zotero library.

        Args:
            query: Search query text
            limit: Maximum number of results to return
            filters: Optional metadata filters
            use_hybrid: Use hybrid search (dense + sparse vectors). If None, uses client default.

        Returns:
            Search results with Zotero item details
        """
        try:
            # Perform semantic search (hybrid or dense-only)
            results = self.qdrant_client.search(
                query_texts=[query],
                n_results=limit,
                where=filters,
                use_hybrid=use_hybrid
            )

            # Enrich results with full Zotero item data
            enriched_results = self._enrich_search_results(results, query)

            return {
                "query": query,
                "limit": limit,
                "filters": filters,
                "results": enriched_results,
                "total_found": len(enriched_results)
            }

        except Exception as e:
            import traceback
            logger.error(f"Error performing semantic search: {e}")
            logger.error(f"Traceback: {traceback.format_exc()}")
            return {
                "query": query,
                "limit": limit,
                "filters": filters,
                "results": [],
                "total_found": 0,
                "error": str(e)
            }

    def graph_search(self,
                    query: str,
                    entity_types: Optional[List[str]] = None,
                    limit: int = 10) -> Dict[str, Any]:
        """
        Search the knowledge graph for entities and concepts.

        Args:
            query: Search query
            entity_types: Filter by entity types
            limit: Maximum number of results

        Returns:
            Graph search results
        """
        if not self.neo4j_client:
            return {
                "query": query,
                "results": [],
                "error": "Neo4j GraphRAG is not enabled"
            }

        try:
            entities = self.neo4j_client.search_entities(
                query=query,
                entity_types=entity_types,
                limit=limit
            )

            return {
                "query": query,
                "entity_types": entity_types,
                "results": entities,
                "total_found": len(entities)
            }

        except Exception as e:
            logger.error(f"Error performing graph search: {e}")
            return {
                "query": query,
                "results": [],
                "error": str(e)
            }

    def find_related_papers(self,
                           paper_key: str,
                           limit: int = 10) -> Dict[str, Any]:
        """
        Find papers related to a given paper via the knowledge graph.

        Args:
            paper_key: Zotero item key
            limit: Maximum number of results

        Returns:
            Related papers with shared entities
        """
        if not self.neo4j_client:
            return {
                "paper_key": paper_key,
                "results": [],
                "error": "Neo4j GraphRAG is not enabled"
            }

        try:
            related = self.neo4j_client.find_related_papers(
                paper_key=paper_key,
                limit=limit
            )

            return {
                "paper_key": paper_key,
                "results": related,
                "total_found": len(related)
            }

        except Exception as e:
            logger.error(f"Error finding related papers: {e}")
            return {
                "paper_key": paper_key,
                "results": [],
                "error": str(e)
            }

    def hybrid_vector_graph_search(self,
                                  query: str,
                                  limit: int = 10,
                                  vector_weight: float = 0.7) -> Dict[str, Any]:
        """
        Perform hybrid search combining vector similarity and graph relationships.

        Args:
            query: Search query
            limit: Maximum number of results
            vector_weight: Weight for vector results (0-1), graph weight is (1 - vector_weight)

        Returns:
            Combined search results
        """
        try:
            # Get vector search results
            vector_results = self.search(query=query, limit=limit*2)
            vector_papers = {r["item_key"]: r for r in vector_results.get("results", [])}

            # If Neo4j is enabled, enhance with graph relationships
            if self.neo4j_client:
                # Get graph entities related to query
                graph_results = self.graph_search(query=query, limit=20)
                graph_entities = graph_results.get("results", [])

                # For each vector result, check graph connections
                enhanced_results = []
                for paper_key, paper in vector_papers.items():
                    # Get related papers from graph
                    related = self.find_related_papers(paper_key, limit=5)
                    paper["related_papers_count"] = len(related.get("results", []))
                    paper["sample_related"] = [r["title"] for r in related.get("results", [])[:3]]

                    # Calculate combined score
                    vector_score = paper.get("similarity_score", 0)
                    graph_boost = min(paper["related_papers_count"] / 10.0, 0.3)  # Max 30% boost
                    paper["combined_score"] = vector_score * vector_weight + graph_boost * (1 - vector_weight)

                    enhanced_results.append(paper)

                # Sort by combined score
                enhanced_results.sort(key=lambda x: x.get("combined_score", 0), reverse=True)

                return {
                    "query": query,
                    "search_type": "hybrid_vector_graph",
                    "results": enhanced_results[:limit],
                    "total_found": len(enhanced_results),
                    "graph_enabled": True
                }
            else:
                # Return just vector results if no graph
                return {
                    "query": query,
                    "search_type": "vector_only",
                    "results": list(vector_papers.values())[:limit],
                    "total_found": len(vector_papers),
                    "graph_enabled": False
                }

        except Exception as e:
            logger.error(f"Error performing hybrid search: {e}")
            return {
                "query": query,
                "results": [],
                "error": str(e)
            }

    def enhanced_semantic_search(self,
                                query: str,
                                limit: int = 10,
                                include_chunk_entities: bool = True,
                                filters: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Enhanced semantic search using bidirectional Qdrant↔Neo4j linking.

        Implements Figure 3 pattern from Qdrant GraphRAG documentation:
        1. Query vectorization and semantic search in Qdrant
        2. Extract Qdrant point IDs from results (e.g., "ABCD1234_chunk_5")
        3. Use point IDs to directly query Neo4j chunks for entities
        4. Enrich each result with chunk-specific entities and relationships

        This is more precise than hybrid_vector_graph_search() which uses
        paper-level relationships. This method retrieves entities from the
        exact chunks that matched the query.

        Args:
            query: Search query text
            limit: Maximum number of results
            include_chunk_entities: Whether to retrieve Neo4j entities (default: True)
            filters: Optional Qdrant metadata filters

        Returns:
            Search results enriched with chunk-level entities from Neo4j

        Example:
            results = search.enhanced_semantic_search(
                query="neural networks for image classification",
                limit=10
            )
            # Each result contains:
            # - item_key, title, abstract (Zotero metadata)
            # - chunk_text, chunk_id (from Qdrant)
            # - entities: [{name: "Convolutional Neural Network", type: "Method"}, ...]
            #   (from Neo4j, specific to this chunk)
        """
        try:
            # Step 1-2: Semantic search in Qdrant
            logger.debug(f"Step 1-2: Performing semantic search in Qdrant for: '{query}'")
            qdrant_results = self.qdrant_client.search(
                query_texts=[query],
                n_results=limit,
                where=filters,
                use_hybrid=True  # Use hybrid search for best results
            )

            # Enrich with Zotero metadata
            enriched_results = self._enrich_search_results(qdrant_results, query)

            # Step 3-4: Use point IDs to get chunk entities from Neo4j
            if include_chunk_entities and self.neo4j_client and enriched_results:
                logger.debug(f"Step 3-4: Retrieving chunk-level entities from Neo4j")

                # Extract Qdrant point IDs from results
                # Point IDs are stored in the 'id' field after enrichment
                point_ids = []
                point_id_to_result = {}

                for result in enriched_results:
                    # Extract the Qdrant point ID (string like "ABCD1234_chunk_5")
                    point_id = result.get("qdrant_point_id")
                    if point_id:
                        point_ids.append(str(point_id))
                        point_id_to_result[str(point_id)] = result

                if point_ids:
                    # Query Neo4j for entities in these specific chunks
                    chunk_entities = self.neo4j_client.get_entities_for_chunks(
                        qdrant_point_ids=point_ids,
                        limit_per_chunk=10
                    )

                    # Attach entities to corresponding results
                    for point_id, entities in chunk_entities.items():
                        if point_id in point_id_to_result:
                            result = point_id_to_result[point_id]
                            result["chunk_entities"] = entities
                            result["chunk_entity_count"] = len(entities)

                            # Extract unique entity types and names for summary
                            entity_types = list(set(
                                t for e in entities
                                for t in e.get("types", [])
                                if t not in ["Entity"]  # Skip base Entity type
                            ))
                            entity_names = [e.get("name") for e in entities[:5]]  # First 5

                            result["entity_types"] = entity_types
                            result["sample_entities"] = entity_names

                    logger.info(f"Enhanced {len(chunk_entities)} results with chunk-level entities")
                else:
                    logger.debug("No point IDs found in results to query Neo4j")

            return {
                "query": query,
                "limit": limit,
                "filters": filters,
                "search_type": "enhanced_semantic" if include_chunk_entities else "standard_semantic",
                "results": enriched_results,
                "total_found": len(enriched_results),
                "neo4j_enabled": self.neo4j_client is not None and include_chunk_entities
            }

        except Exception as e:
            import traceback
            logger.error(f"Error performing enhanced semantic search: {e}")
            logger.error(f"Traceback: {traceback.format_exc()}")
            return {
                "query": query,
                "limit": limit,
                "filters": filters,
                "results": [],
                "total_found": 0,
                "error": str(e)
            }

    def _enrich_search_results(self, qdrant_results: Dict[str, Any], query: str) -> List[Dict[str, Any]]:
        """Enrich Qdrant results with full Zotero item data."""
        enriched = []

        # Check if we have results
        if not qdrant_results.get("ids") or not qdrant_results["ids"]:
            return enriched

        # Safely extract nested lists with proper bounds checking
        ids_nested = qdrant_results.get("ids", [])
        if not ids_nested or not ids_nested[0]:
            return enriched

        ids = ids_nested[0]
        distances_nested = qdrant_results.get("distances", [[]])
        documents_nested = qdrant_results.get("documents", [[]])
        metadatas_nested = qdrant_results.get("metadatas", [[]])

        # Extract first element safely, defaulting to empty list if not present
        distances = distances_nested[0] if distances_nested and len(distances_nested) > 0 else []
        documents = documents_nested[0] if documents_nested and len(documents_nested) > 0 else []
        metadatas = metadatas_nested[0] if metadatas_nested and len(metadatas_nested) > 0 else []

        for i, point_id in enumerate(ids):
            try:
                # Extract the actual Zotero item key from metadata (point_id is a UUID)
                item_key = metadatas[i].get("item_key", "") if i < len(metadatas) else ""
                if not item_key:
                    logger.warning(f"No item_key found in metadata for point_id {point_id}")
                    continue

                # If this is a chunk (item_key ends with _chunk_N), use parent_item_key
                if "_chunk_" in item_key:
                    parent_key = metadatas[i].get("parent_item_key", "")
                    if parent_key:
                        logger.debug(f"Resolved chunk {item_key} to parent {parent_key}")
                        zotero_key = parent_key
                    else:
                        # Fallback: strip chunk suffix manually
                        zotero_key = item_key.split("_chunk_")[0]
                        logger.debug(f"No parent_item_key, stripping suffix: {item_key} -> {zotero_key}")
                else:
                    zotero_key = item_key

                # Get full item data from Zotero
                zotero_item = self.zotero_client.item(zotero_key)

                enriched_result = {
                    "item_key": zotero_key,  # Use parent key for Claude, not chunk key
                    "original_chunk_key": item_key if "_chunk_" in item_key else None,  # Preserve chunk info
                    "qdrant_point_id": item_key,  # String ID like "ABCD1234_chunk_5" for Neo4j linking
                    "similarity_score": 1 - distances[i] if i < len(distances) else 0,
                    "matched_text": documents[i] if i < len(documents) else "",
                    "metadata": metadatas[i] if i < len(metadatas) else {},
                    "zotero_item": zotero_item,
                    "query": query
                }

                enriched.append(enriched_result)
                
            except Exception as e:
                logger.error(f"Error enriching result for item {item_key}: {e}")
                # Include basic result even if enrichment fails
                enriched.append({
                    "item_key": item_key,
                    "similarity_score": 1 - distances[i] if i < len(distances) else 0,
                    "matched_text": documents[i] if i < len(documents) else "",
                    "metadata": metadatas[i] if i < len(metadatas) else {},
                    "query": query,
                    "error": f"Could not fetch full item data: {e}"
                })
        
        return enriched
    
    def get_database_status(self) -> Dict[str, Any]:
        """Get status information about the semantic search database."""
        collection_info = self.qdrant_client.get_collection_info()

        return {
            "collection_info": collection_info,
            "update_config": self.update_config,
            "should_update": self.should_update_database(),
            "last_update": self.update_config.get("last_update"),
        }

    def delete_item(self, item_key: str) -> bool:
        """Delete an item from the semantic search database."""
        try:
            self.qdrant_client.delete_documents([item_key])
            return True
        except Exception as e:
            logger.error(f"Error deleting item {item_key}: {e}")
            return False


def create_semantic_search(config_path: Optional[str] = None) -> ZoteroSemanticSearch:
    """
    Create a ZoteroSemanticSearch instance.
    
    Args:
        config_path: Path to configuration file
        
    Returns:
        Configured ZoteroSemanticSearch instance
    """
    return ZoteroSemanticSearch(config_path=config_path)