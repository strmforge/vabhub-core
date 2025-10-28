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
    name="vabhub",
    version="1.3.0",
    packages=find_packages(),
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