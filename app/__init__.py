"""
VabHub Core Application Package

This package contains the main FastAPI application and API routes.
"""

__version__ = "1.0.0"
__author__ = "VabHub Team"
__email__ = "team@vabhub.org"

from .main import create_app

__all__ = ["create_app"]