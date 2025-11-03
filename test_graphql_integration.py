"""
Test script for GraphQL API integration
"""

import sys
import os

# Add the core directory to Python path
sys.path.insert(0, os.path.dirname(__file__))

def test_graphql_import():
    """Test if GraphQL modules can be imported successfully"""
    try:
        # Test GraphQL schema import
        from core.graphql_schema import schema
        print("✅ GraphQL schema imported successfully")
        
        # Test GraphQL API import
        from core.graphql_api import GraphQLAPI
        print("✅ GraphQL API imported successfully")
        
        # Test API integration
        from core.config import Config
        config = Config()
        
        # Create GraphQL API instance
        graphql_api = GraphQLAPI(config)
        print("✅ GraphQL API instance created successfully")
        
        # Test router creation
        router = graphql_api.get_router()
        print("✅ GraphQL router created successfully")
        
        print("\n🎉 GraphQL API integration test passed!")
        print("📊 GraphQL endpoint will be available at: /graphql")
        print("🔧 GraphQL playground will be available at: /graphql")
        
        return True
        
    except ImportError as e:
        print(f"❌ Import error: {e}")
        return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

if __name__ == "__main__":
    print("Testing GraphQL API integration...")
    success = test_graphql_import()
    sys.exit(0 if success else 1)