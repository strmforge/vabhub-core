"""
VabHub Core - Media Management and Automation System
"""

from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

with open("requirements.txt", "r", encoding="utf-8") as fh:
    requirements = [line.strip() for line in fh if line.strip() and not line.startswith("#")]

setup(
    name="vabhub-core",
    version="0.1.0",
    author="VabHub Team",
    author_email="team@vabhub.com",
    description="Core components for VabHub - A media management and automation system",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/strmforge/vabhub-Core",
    packages=find_packages(where="core"),
    package_dir={"": "core"},
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
    ],
    python_requires=">=3.8",
    install_requires=requirements,
    extras_require={
        "dev": [
            "pytest>=6.0",
            "pytest-asyncio",
            "black",
            "mypy",
            "sphinx",
        ],
    },
    entry_points={
        "console_scripts": [
            "vabhub=vabhub.main:main",
        ],
    },
)