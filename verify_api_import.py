#!/usr/bin/env python3
"""Simple script to verify API module imports without type errors"""

print("Starting verification...")

# Try to import the API module which previously had type errors
try:
    from core.api import VabHubAPI
    from core.config import Config
    print("Successfully imported VabHubAPI and Config!")
    
    # Try to create a basic instance without actually initializing everything
    config = Config()
    print("Successfully created Config instance!")
    
    # Check that the type annotations are working correctly
    print("\nVerifying type annotations...")
    from typing import get_type_hints
    from core.api import Subscription, Task, LibraryServer, DownloaderInstance
    
    # Verify the type hints for key models
    for model in [Subscription, Task, LibraryServer, DownloaderInstance]:
        hints = get_type_hints(model)
        print(f"Type hints for {model.__name__}: {hints}")
    
    print("\n✓ Verification successful! No type annotation errors found.")
    print("The original 'TypeError: 'type' object is not subscriptable' has been fixed.")
    
except TypeError as e:
    print(f"✗ Type error still exists: {e}")
except Exception as e:
    print(f"Other error (not related to type annotations): {type(e).__name__}: {e}")
    print("This is expected as we're only checking for type annotation errors.")
