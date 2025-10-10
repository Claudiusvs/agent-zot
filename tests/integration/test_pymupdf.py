#!/usr/bin/env python3
"""Test PyMuPDF parser"""
import sys
sys.path.insert(0, '.')

from agent_zot.parsers.pymupdf import PyMuPDFParser

# Test with a sample PDF
pdf_path = '/Users/claudiusv.schroder/zotero_database/storage/NNVLKQD3/Bornscheuer et al. - 2024 - Mapping resilience a scoping review on mediators and moderators of childhood adversity with a focus.pdf'

print('Testing PyMuPDF parser...')
parser = PyMuPDFParser(max_tokens=512)

result = parser.parse_pdf(pdf_path)

print(f'\n✅ SUCCESS!')
print(f'  Text length: {len(result["text"])} chars')
print(f'  Chunks: {result["metadata"]["num_chunks"]}')
print(f'  Pages: {result["metadata"]["num_pages"]}')
print(f'  Preview: {result["text"][:200]}...')
