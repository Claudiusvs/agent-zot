"""
Docling integration for advanced document parsing.

This module provides enhanced PDF and document parsing using Docling,
with DoclingParseV2DocumentBackend for 10x faster processing and
conditional OCR fallback for scanned PDFs.
"""

import logging
import os
from pathlib import Path
from typing import List, Dict, Any, Optional
import tempfile

from docling.document_converter import DocumentConverter, PdfFormatOption
from docling.chunking import HybridChunker
from docling.datamodel.pipeline_options import PdfPipelineOptions, AcceleratorOptions, EasyOcrOptions
from docling.datamodel.base_models import InputFormat
from docling.backend.docling_parse_v2_backend import DoclingParseV2DocumentBackend
from docling.backend.docling_parse_backend import DoclingParseDocumentBackend

logger = logging.getLogger(__name__)


class DoclingParser:
    """Enhanced document parser using Docling with V2 backend and conditional OCR."""

    def __init__(self,
                 tokenizer: str = "sentence-transformers/all-MiniLM-L6-v2",
                 max_tokens: Optional[int] = None,
                 merge_peers: bool = True,
                 num_threads: int = 10,
                 do_formula_enrichment: bool = False,
                 do_table_structure: bool = False,
                 enable_ocr_fallback: bool = True,
                 ocr_min_text_threshold: int = 100):
        """
        Initialize Docling parser with V2 backend and conditional OCR fallback.

        Args:
            tokenizer: HuggingFace tokenizer model name (should match embedding model)
            max_tokens: Maximum tokens per chunk (if None, uses tokenizer's default)
            merge_peers: Whether to merge undersized chunks with same metadata (default: True)
            num_threads: Number of CPU threads for parallel processing (default: 10)
            do_formula_enrichment: Convert LaTeX formulas to text (default: False)
            do_table_structure: Parse table structure (default: False)
            enable_ocr_fallback: Enable OCR fallback for scanned PDFs (default: True)
            ocr_min_text_threshold: Minimum chars before considering OCR needed (default: 100)
        """
        self.tokenizer = tokenizer
        self.max_tokens = max_tokens
        self.merge_peers = merge_peers
        self.enable_ocr_fallback = enable_ocr_fallback
        self.ocr_min_text_threshold = ocr_min_text_threshold
        self.num_threads = num_threads
        self.do_formula_enrichment = do_formula_enrichment
        self.do_table_structure = do_table_structure

        # Configure V2 backend (fast, no OCR) - primary converter
        v2_pipeline_options = PdfPipelineOptions(
            do_formula_enrichment=do_formula_enrichment,
            do_table_structure=do_table_structure,
            accelerator_options=AcceleratorOptions(
                num_threads=num_threads,
                device="auto"  # MPS GPU acceleration on Apple Silicon
            )
        )
        v2_pipeline_options.do_ocr = False  # Explicitly disable OCR for V2 backend

        self.v2_converter = DocumentConverter(
            format_options={
                InputFormat.PDF: PdfFormatOption(
                    pipeline_options=v2_pipeline_options,
                    backend=DoclingParseV2DocumentBackend  # 10x faster, no OCR
                )
            }
        )

        # Configure standard backend with OCR (fallback for scanned PDFs)
        if enable_ocr_fallback:
            ocr_pipeline_options = PdfPipelineOptions(
                do_formula_enrichment=do_formula_enrichment,
                do_table_structure=do_table_structure,
                ocr_options=EasyOcrOptions(
                    lang=["en"],  # Add more languages as needed
                    force_full_page_ocr=True  # Full OCR for scanned documents
                ),
                accelerator_options=AcceleratorOptions(
                    num_threads=num_threads,
                    device="auto"
                )
            )

            self.ocr_converter = DocumentConverter(
                format_options={
                    InputFormat.PDF: PdfFormatOption(
                        pipeline_options=ocr_pipeline_options,
                        backend=DoclingParseDocumentBackend  # Standard backend with OCR
                    )
                }
            )
        else:
            self.ocr_converter = None

        # Use HybridChunker for token-aware, structure-preserving chunking
        chunker_params = {
            "tokenizer": tokenizer,
            "merge_peers": merge_peers,
            "delim": "\n"
        }

        # Only add max_tokens if explicitly provided
        if max_tokens is not None:
            chunker_params["max_tokens"] = max_tokens

        self.chunker = HybridChunker(**chunker_params)

        logger.info(f"DoclingParser initialized with V2 backend (OCR fallback: {enable_ocr_fallback})")
        logger.info(f"HybridChunker config: tokenizer={tokenizer}, max_tokens={self.chunker.max_tokens}")

    def parse_pdf(self, pdf_path: str, force_ocr: bool = False) -> Dict[str, Any]:
        """
        Parse a PDF file using V2 backend with conditional OCR fallback.

        Strategy:
        1. Try V2 backend first (fast, no OCR)
        2. If extracted text < threshold AND OCR fallback enabled, retry with OCR
        3. Return parsed document with metadata

        Args:
            pdf_path: Path to the PDF file
            force_ocr: Force OCR processing (default: False)

        Returns:
            Dictionary containing parsed document with structure:
            {
                "text": str,  # Full document text
                "chunks": List[Dict],  # Chunks with metadata
                "tables": List[Dict],  # Extracted tables
                "figures": List[Dict],  # Extracted figures
                "metadata": Dict  # Document metadata including used_ocr flag
            }
        """
        used_ocr = False

        try:
            # First attempt: V2 backend (fast, no OCR)
            if not force_ocr:
                logger.debug(f"Attempting V2 backend parse (no OCR): {Path(pdf_path).name}")
                result = self.v2_converter.convert(pdf_path)
                doc = result.document
                full_text = doc.export_to_markdown()

                # Check if we got sufficient text
                text_length = len(full_text.strip())

                if text_length < self.ocr_min_text_threshold and self.enable_ocr_fallback and self.ocr_converter:
                    # Text extraction failed - retry with OCR
                    logger.warning(f"Insufficient text extracted ({text_length} chars < {self.ocr_min_text_threshold}) - retrying with OCR: {Path(pdf_path).name}")
                    result = self.ocr_converter.convert(pdf_path)
                    doc = result.document
                    full_text = doc.export_to_markdown()
                    used_ocr = True
                    logger.info(f"OCR fallback successful: {Path(pdf_path).name}")
                elif text_length < self.ocr_min_text_threshold:
                    logger.warning(f"Insufficient text extracted ({text_length} chars), but OCR fallback disabled: {Path(pdf_path).name}")
                else:
                    logger.debug(f"V2 backend successful ({text_length} chars): {Path(pdf_path).name}")
            else:
                # Force OCR requested
                if not self.enable_ocr_fallback or not self.ocr_converter:
                    raise ValueError("OCR requested but fallback is disabled")
                logger.info(f"Force OCR requested: {Path(pdf_path).name}")
                result = self.ocr_converter.convert(pdf_path)
                doc = result.document
                full_text = doc.export_to_markdown()
                used_ocr = True

            # Create chunks with hierarchy preservation
            chunks = []
            chunk_iter = self.chunker.chunk(doc)

            for i, chunk in enumerate(chunk_iter):
                # Extract headings
                headings = []
                if chunk.meta.headings:
                    for h in chunk.meta.headings:
                        if isinstance(h, str):
                            headings.append(h)
                        elif hasattr(h, 'text'):
                            headings.append(h.text)
                        else:
                            headings.append(str(h))

                chunk_data = {
                    "chunk_id": i,
                    "text": self.chunker.serialize(chunk),
                    "meta": {
                        "doc_items": [item.self_ref for item in chunk.meta.doc_items] if chunk.meta.doc_items else [],
                        "headings": headings
                    }
                }
                chunks.append(chunk_data)

            # Extract tables
            tables = []
            for item in doc.tables:
                table_data = {
                    "content": item.export_to_markdown(),
                    "caption": getattr(item, 'caption', None),
                    "page": getattr(item, 'page', None)
                }
                tables.append(table_data)

            # Extract figures
            figures = []
            for item in doc.pictures:
                figure_data = {
                    "caption": getattr(item, 'caption', None),
                    "page": getattr(item, 'page', None)
                }
                figures.append(figure_data)

            # Extract metadata
            metadata = {
                "num_pages": len(doc.pages) if hasattr(doc, 'pages') else None,
                "num_chunks": len(chunks),
                "num_tables": len(tables),
                "num_figures": len(figures),
                "used_ocr": used_ocr,  # Track whether OCR was used
                "text_length": len(full_text.strip())
            }

            return {
                "text": full_text,
                "chunks": chunks,
                "tables": tables,
                "figures": figures,
                "metadata": metadata
            }

        except Exception as e:
            logger.error(f"Error parsing PDF {Path(pdf_path).name}: {e}")
            raise  # Fail loudly - no silent degradation

    def parse_file(self, file_path: str) -> Dict[str, Any]:
        """
        Parse any supported document format.

        Args:
            file_path: Path to the document file

        Returns:
            Parsed document dictionary
        """
        file_extension = Path(file_path).suffix.lower()

        if file_extension == '.pdf':
            return self.parse_pdf(file_path)
        else:
            # Docling supports many formats - use V2 backend
            try:
                result = self.v2_converter.convert(file_path)
                doc = result.document

                full_text = doc.export_to_markdown()
                chunk_iter = self.chunker.chunk(doc)

                chunks = []
                for i, chunk in enumerate(chunk_iter):
                    chunks.append({
                        "chunk_id": i,
                        "text": self.chunker.serialize(chunk),
                        "meta": {}
                    })

                return {
                    "text": full_text,
                    "chunks": chunks,
                    "tables": [],
                    "figures": [],
                    "metadata": {
                        "num_chunks": len(chunks),
                        "file_type": file_extension,
                        "used_ocr": False
                    }
                }
            except Exception as e:
                logger.error(f"Error parsing file {file_path}: {e}")
                raise


def parse_zotero_attachment(attachment_path: str,
                            chunk_size: int = 1000,
                            chunk_overlap: int = 200) -> Dict[str, Any]:
    """
    Parse a Zotero attachment file using Docling.

    Args:
        attachment_path: Path to the attachment file
        chunk_size: Target chunk size
        chunk_overlap: Chunk overlap size

    Returns:
        Parsed document dictionary
    """
    parser = DoclingParser(chunk_size=chunk_size, chunk_overlap=chunk_overlap)
    return parser.parse_file(attachment_path)
