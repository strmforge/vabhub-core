#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
VabHub Core Package
A comprehensive media management and automation framework.
"""

from setuptools import setup, find_packages

setup(
    name="vabhub-core",
    version="1.5.0",
    packages=find_packages(include=['app', 'core', 'api']),
    install_requires=[
        "fastapi>=0.104.1",
        "uvicorn>=0.24.0",
        "httpx>=0.25.0",
        "pydantic>=2.5.0",
        "sqlalchemy>=2.0.23",
        "alembic>=1.12.1",
        "redis>=5.0.1",
        "celery>=5.3.4",
        "pyyaml>=6.0.1",
        "requests>=2.31.0",
        "python-dotenv>=1.0.0",
        "cryptography>=41.0.7",
        "asyncio-mqtt>=0.12.0",
        "click>=8.1.7",
        "colorama>=0.4.6",
        "python-multipart>=0.0.6",
        "jinja2>=3.1.2",
        "pytest>=7.4.3",
        "pytest-asyncio>=0.21.1",
        "websockets>=12.0",
        "apscheduler>=3.10.4",
        "prometheus-client>=0.19.0",
        "psutil>=5.9.6",
        "structlog>=23.2.0",
    ],
    extras_require={
        "dev": [
            "pytest-cov>=4.1.0",
            "black>=23.9.1",
            "isort>=5.12.0",
            "flake8>=6.1.0",
            "mypy>=1.6.1"
        ],
        "test": [
            "pytest>=7.4.3",
            "pytest-asyncio>=0.21.1",
            "httpx>=0.25.0"
        ]
    },
    python_requires=">=3.8",
    author="VabHub Team",
    author_email="vabhub@example.com",
    description="A comprehensive media management and automation framework",
    long_description=open("README.md", encoding="utf-8").read(),
    long_description_content_type="text/markdown",
    url="https://github.com/vabhub/vabhub-core",
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
    ],
)