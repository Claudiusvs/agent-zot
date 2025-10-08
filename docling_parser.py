"""
Docling integration for advanced document parsing.

This module provides enhanced PDF and document parsing using Docling,
with support for tables, figures, and hierarchical document structure.
"""

import logging
from pathlib import Path
from typing import List, Dict, Any, Optional
import tempfile
import os

from docling.document_converter import DocumentConverter, PdfFormatOption
from docling.chunking import HybridChunker
from docling.datamodel.pipeline_options import PdfPipelineOptions, AcceleratorOptions

logger = logging.getLogger(__name__)


class DoclingParser:
    """Enhanced document parser using Docling."""

    def __init__(self,
                 tokenizer: str = "sentence-transformers/all-MiniLM-L6-v2",
                 max_tokens: Optional[int] = None,
                 merge_peers: bool = True,
                 num_threads: int = 10,
                 do_formula_enrichment: bool = True,
                 do_table_structure: bool = True,
                 do_ocr: bool = True,
                 ocr_min_text_threshold: int = 100):
        """
        Initialize Docling parser with HybridChunker.

        Args:
            tokenizer: HuggingFace tokenizer model name (should match embedding model)
            max_tokens: Maximum tokens per chunk (if None, uses tokenizer's default)
            merge_peers: Whether to merge undersized chunks with same metadata (default: True)
            num_threads: Number of CPU threads for parallel processing (default: 10)
            do_formula_enrichment: Convert LaTeX formulas to text (default: True)
            do_table_structure: Parse table structure (default: True)
            do_ocr: Enable OCR for scanned PDFs (default: True)
            ocr_min_text_threshold: Minimum chars before considering OCR needed (default: 100)
        """
        self.tokenizer = tokenizer
        self.max_tokens = max_tokens
        self.merge_peers = merge_peers
        self.ocr_min_text_threshold = ocr_min_text_threshold

        # Configure PDF pipeline options with all settings
        self.pipeline_options = PdfPipelineOptions(
            do_formula_enrichment=do_formula_enrichment,
            do_table_structure=do_table_structure,
            do_ocr=do_ocr,
            accelerator_options=AcceleratorOptions(
                num_threads=num_threads,
                device="auto"
            )
        )

        # Create converter with pipeline options using PdfFormatOption
        self.converter = DocumentConverter(
            format_options={PdfFormatOption: self.pipeline_options}
        )

        # Use HybridChunker for token-aware, structure-preserving chunking
        chunker_params = {
            "tokenizer": tokenizer,
            "merge_peers": merge_peers,
            "delim": "\n"
        }

        # Only add max_tokens if explicitly provided
        # Otherwise, let HybridChunker use tokenizer's default
        if max_tokens is not None:
            chunker_params["max_tokens"] = max_tokens

        self.chunker = HybridChunker(**chunker_params)

        logger.info(f"DoclingParser initialized with HybridChunker (tokenizer: {tokenizer}, max_tokens: {self.chunker.max_tokens})")

    def parse_pdf(self, pdf_path: str, force_ocr: bool = False) -> Dict[str, Any]:
        """
        Parse a PDF file using Docling with conditional OCR fallback.

        Args:
            pdf_path: Path to the PDF file
            force_ocr: Force OCR processing (default: False, OCR used only when needed)

        Returns:
            Dictionary containing parsed document with structure:
            {
                "text": str,  # Full document text
                "chunks": List[Dict],  # Chunks with metadata
                "tables": List[Dict],  # Extracted tables
                "figures": List[Dict],  # Extracted figures
                "metadata": Dict  # Document metadata
            }
        """
        try:
            # Parse with standard converter (OCR already enabled in pipeline options)
            result = self.converter.convert(pdf_path)
            doc = result.document

            # Check if we got minimal content
            full_text = doc.export_to_markdown()
            if len(full_text.strip()) < self.ocr_min_text_threshold:
                logger.warning(f"Minimal text extracted ({len(full_text)} chars) - may be scanned PDF")

            # Extract full text
            full_text = doc.export_to_markdown()

            # Create chunks with hierarchy preservation
            chunks = []
            chunk_iter = self.chunker.chunk(doc)

            for i, chunk in enumerate(chunk_iter):
                # Extract headings - they might be strings or objects with .text attribute
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
                "num_figures": len(figures)
            }

            return {
                "text": full_text,
                "chunks": chunks,
                "tables": tables,
                "figures": figures,
                "metadata": metadata
            }

        except Exception as e:
            logger.error(f"Error parsing PDF with Docling: {e}")

            # Fallback to simple text extraction
            return self._fallback_parse(pdf_path)

    def _fallback_parse(self, pdf_path: str) -> Dict[str, Any]:
        """
        Fallback parser using simple text extraction.

        Args:
            pdf_path: Path to the PDF file

        Returns:
            Dictionary with basic parsing
        """
        try:
            import pypdfium2 as pdfium

            pdf = pdfium.PdfDocument(pdf_path)
            text_parts = []

            for page_num in range(len(pdf)):
                page = pdf[page_num]
                textpage = page.get_textpage()
                text = textpage.get_text_range()
                text_parts.append(text)

            full_text = "\n\n".join(text_parts)

            # Create simple chunks
            chunks = self._simple_chunk(full_text)

            return {
                "text": full_text,
                "chunks": chunks,
                "tables": [],
                "figures": [],
                "metadata": {
                    "num_pages": len(pdf),
                    "num_chunks": len(chunks),
                    "num_tables": 0,
                    "num_figures": 0,
                    "fallback": True
                }
            }
        except Exception as e:
            logger.error(f"Fallback PDF parsing also failed: {e}")
            raise

    def _simple_chunk(self, text: str) -> List[Dict[str, Any]]:
        """
        Create simple text chunks with overlap.

        Args:
            text: Full document text

        Returns:
            List of chunk dictionaries
        """
        chunks = []
        chunk_size = 1000  # Simple fallback chunk size
        overlap = 100  # Simple fallback overlap

        start = 0
        chunk_id = 0

        while start < len(text):
            end = start + chunk_size
            chunk_text = text[start:end]

            chunks.append({
                "chunk_id": chunk_id,
                "text": chunk_text,
                "meta": {
                    "start_char": start,
                    "end_char": min(end, len(text))
                }
            })

            start = end - overlap
            chunk_id += 1

        return chunks

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
            # Docling supports many formats - let it handle them
            try:
                result = self.converter.convert(file_path)
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
                        "file_type": file_extension
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
