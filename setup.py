from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

with open("requirements.txt", "r", encoding="utf-8") as fh:
    requirements = [line.strip() for line in fh if line.strip() and not line.startswith("#")]

setup(
    name="vabhub-core",
    version="1.0.0",
    author="VabHub Team",
    author_email="team@vabhub.org",
    description="VabHub Core Backend Service - Media Management System",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/vabhub/vabhub-core",
    packages=find_packages(),
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
    ],
    python_requires=">=3.8",
    install_requires=requirements,
    extras_require={
        "dev": [
            "pytest>=6.0",
            "pytest-asyncio>=0.15",
            "black>=21.0",
            "isort>=5.0",
            "flake8>=3.9",
            "mypy>=0.910",
        ],
        "plugins": [
            "vabhub-plugins>=1.0.0",
        ],
        "resources": [
            "vabhub-resources>=1.0.0",
        ],
    },
    entry_points={
        "console_scripts": [
            "vabhub-core=vabhub_core.cli:main",
        ],
    },
    include_package_data=True,
    package_data={
        "vabhub_core": [
            "config/*.yaml",
            "config/*.json",
            "templates/*.html",
            "static/*",
        ],
    },
)