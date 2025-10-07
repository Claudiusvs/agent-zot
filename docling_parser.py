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

from docling.document_converter import DocumentConverter
from docling_core.transforms.chunker import HierarchicalChunker

logger = logging.getLogger(__name__)


class DoclingParser:
    """Enhanced document parser using Docling."""

    def __init__(self,
                 chunk_size: int = 512,
                 chunk_overlap: int = 100,
                 merge_list_items: bool = True):
        """
        Initialize Docling parser.

        Args:
            chunk_size: Target size for document chunks (in characters, not tokens)
            chunk_overlap: Overlap between chunks (in characters)
            merge_list_items: Whether to merge successive list items (default: True)
        """
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.converter = DocumentConverter()

        # Use HierarchicalChunker with document structure awareness
        self.chunker = HierarchicalChunker(
            merge_list_items=merge_list_items,
            delim="\n"
        )

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
            # Try standard parsing first
            if force_ocr:
                logger.info(f"Force OCR enabled for {pdf_path}")
                result = self.converter.convert(pdf_path, do_ocr=True, force_full_page_ocr=True)
            else:
                result = self.converter.convert(pdf_path)

            doc = result.document

            # Check if we got minimal content (might indicate OCR needed)
            full_text = doc.export_to_markdown()
            if not force_ocr and len(full_text.strip()) < 100:
                logger.warning(f"Minimal text extracted ({len(full_text)} chars), retrying with OCR")
                result = self.converter.convert(pdf_path, do_ocr=True, force_full_page_ocr=True)
                doc = result.document

            # Extract full text
            full_text = doc.export_to_markdown()

            # Create chunks with hierarchy preservation
            chunks = []
            chunk_iter = self.chunker.chunk(doc)

            for i, chunk in enumerate(chunk_iter):
                chunk_data = {
                    "chunk_id": i,
                    "text": chunk.text,
                    "meta": {
                        "doc_items": [item.self_ref for item in chunk.meta.doc_items] if chunk.meta.doc_items else [],
                        "headings": [h.text for h in chunk.meta.headings] if chunk.meta.headings else []
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
            # If standard parsing failed and OCR wasn't tried, try with OCR
            if not force_ocr:
                logger.warning(f"Standard parsing failed: {e}. Trying with OCR...")
                try:
                    return self.parse_pdf(pdf_path, force_ocr=True)
                except Exception as ocr_error:
                    logger.error(f"OCR parsing also failed: {ocr_error}")
            else:
                logger.error(f"Error parsing PDF with Docling (OCR enabled): {e}")

            # Final fallback to simple text extraction
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
        chunk_size = self.chunk_size
        overlap = self.chunk_overlap

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
                        "text": chunk.text,
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
