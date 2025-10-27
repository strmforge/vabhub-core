"""
VabHub Core Business Logic Package

This package contains the core business logic, database models, 
and configuration management for the VabHub system.
"""

__version__ = "1.0.0"

from .config import Config
from .database import Database

__all__ = ["Config", "Database"]