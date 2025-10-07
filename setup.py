from setuptools import setup, find_packages

setup(
    name="zotero-mcp",
    version="0.2.0",
    packages=find_packages(),
    py_modules=[
        '__init__',
        '_version',
        'better_bibtex_client',
        'chroma_client',
        'cli',
        'client',
        'docling_parser',
        'local_db',
        'neo4j_graphrag_client',
        'pdfannots_downloader',
        'pdfannots_helper',
        'qdrant_client_wrapper',
        'semantic_search',
        'server',
        'setup_helper',
        'updater',
        'utils'
    ],
    entry_points={
        'console_scripts': [
            'zotero-mcp=server:main',
        ],
    },
    python_requires='>=3.10',
)
