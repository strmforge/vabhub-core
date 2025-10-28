#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
VabHub 二进制打包配置
采用MoviePilot的安全策略：API密钥硬编码但通过二进制保护
"""

from setuptools import setup, find_packages
from Cython.Build import cythonize
import glob

# 扩展模块配置
extensions = [
    # 核心模块编译保护
    *[f"VabHub-Core/core/{module}.py" for module in [
        "config", "storage_115", "enhanced_error_handler"
    ]],
    # 前端模块
    *[f"VabHub-Frontend/{module}.py" for module in [
        "main", "components/storage"
    ] if Path(f"VabHub-Frontend/{module}.py").exists()]
]

setup(
    name="vabhub-core",
    version="1.3.0",
    packages=find_packages(),
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
        "Cython>=3.0.0"
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
    ext_modules=cythonize(
        extensions,
        build_dir="build",
        compiler_directives={
            "language_level": "3",
            "always_allow_keywords": True,
            "cdivision": True,
            "boundscheck": False,
            "wraparound": False,
            "initializedcheck": False,
            "nonecheck": False
        }
    ),
    script_args=["build_ext", "-j8", "--inplace"],
)