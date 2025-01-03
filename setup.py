"""Setup configuration for HADES package."""

from setuptools import setup, find_packages

setup(
    name="hades",
    version="0.1.0",
    packages=find_packages(),
    install_requires=[
        "pydantic>=2.0.0",
        "python-arango>=7.5.0",
        "pymilvus>=2.2.0",
        "aiohttp>=3.8.0",
        "pytest>=7.0.0",
        "pytest-asyncio>=0.20.0",
        "pytest-cov>=4.0.0",
    ],
    python_requires=">=3.8",
    author="Your Name",
    author_email="your.email@example.com",
    description="HADES - Hybrid ArangoDB and Milvus Database Engine System",
    long_description=open("README.md").read(),
    long_description_content_type="text/markdown",
    url="https://github.com/yourusername/hades",
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
    ],
) 