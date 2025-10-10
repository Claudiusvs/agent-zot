from setuptools import setup, find_packages

setup(
    name="agent-zot",
    version="0.2.0",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    entry_points={
        'console_scripts': [
            'agent-zot=agent_zot.core.cli:main',
            'zotero-mcp=agent_zot.core.cli:main',  # Keep backward compatibility
        ],
    },
    python_requires='>=3.10',
)
