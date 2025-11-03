import pytest
import os
from unittest.mock import patch, mock_open

from core.config import Config, get_config


class TestConfig:
    """Test cases for configuration management."""

    def test_config_default_values(self):
        """Test that config has default values."""
        config = Config()
        
        # Test default values
        assert config.DATABASE_URL == "sqlite:///vabhub.db"
        assert config.REDIS_URL == "redis://localhost:6379/0"
        assert config.CACHE_TTL == 300
        assert config.SECRET_KEY is not None
        assert config.ALGORITHM == "HS256"
        assert config.ACCESS_TOKEN_EXPIRE_MINUTES == 30

    def test_config_environment_override(self):
        """Test environment variable overrides."""
        with patch.dict(os.environ, {
            'DATABASE_URL': 'postgresql://user:pass@localhost/db',
            'REDIS_URL': 'redis://redis:6379/1',
            'CACHE_TTL': '600',
            'SECRET_KEY': 'custom-secret-key',
            'ACCESS_TOKEN_EXPIRE_MINUTES': '60'
        }):
            config = Config()
            
            assert config.DATABASE_URL == 'postgresql://user:pass@localhost/db'
            assert config.REDIS_URL == 'redis://redis:6379/1'
            assert config.CACHE_TTL == 600
            assert config.SECRET_KEY == 'custom-secret-key'
            assert config.ACCESS_TOKEN_EXPIRE_MINUTES == 60

    def test_config_env_file_loading(self):
        """Test loading configuration from .env file."""
        env_content = """
        DATABASE_URL=sqlite:///test.db
        REDIS_URL=redis://localhost:6379/2
        CACHE_TTL=900
        SECRET_KEY=env-file-secret
        ACCESS_TOKEN_EXPIRE_MINUTES=45
        """
        
        with patch('builtins.open', mock_open(read_data=env_content)):
            with patch('os.path.exists', return_value=True):
                config = Config()
                
                # Values should be loaded from .env file
                assert config.DATABASE_URL == 'sqlite:///test.db'
                assert config.REDIS_URL == 'redis://localhost:6379/2'
                assert config.CACHE_TTL == 900
                assert config.SECRET_KEY == 'env-file-secret'
                assert config.ACCESS_TOKEN_EXPIRE_MINUTES == 45

    def test_config_validation(self):
        """Test configuration validation."""
        config = Config()
        
        # Test valid configuration
        assert config.validate() is True
        
        # Test invalid CACHE_TTL
        config.CACHE_TTL = -1
        assert config.validate() is False
        
        # Reset to valid
        config.CACHE_TTL = 300
        assert config.validate() is True
        
        # Test invalid ACCESS_TOKEN_EXPIRE_MINUTES
        config.ACCESS_TOKEN_EXPIRE_MINUTES = -10
        assert config.validate() is False

    def test_config_string_representation(self):
        """Test config string representation."""
        config = Config()
        config_str = str(config)
        
        # Should contain key configuration information
        assert 'DATABASE_URL' in config_str
        assert 'REDIS_URL' in config_str
        assert 'CACHE_TTL' in config_str
        assert 'SECRET_KEY' in config_str

    def test_config_sensitive_data_masking(self):
        """Test that sensitive data is masked in string representation."""
        config = Config()
        config.SECRET_KEY = 'very-secret-key'
        
        config_str = str(config)
        
        # Secret key should be masked
        assert 'very-secret-key' not in config_str
        assert '***' in config_str  # Masked representation

    def test_get_config_singleton(self):
        """Test that get_config returns a singleton instance."""
        config1 = get_config()
        config2 = get_config()
        
        # Should be the same instance
        assert config1 is config2

    def test_config_reload(self):
        """Test configuration reload functionality."""
        config = Config()
        original_database_url = config.DATABASE_URL
        
        # Modify environment and reload
        with patch.dict(os.environ, {'DATABASE_URL': 'sqlite:///reloaded.db'}):
            config.reload()
            assert config.DATABASE_URL == 'sqlite:///reloaded.db'
        
        # Restore original
        config.DATABASE_URL = original_database_url

    def test_config_error_handling(self):
        """Test configuration error handling."""
        # Test invalid environment variable types
        with patch.dict(os.environ, {'CACHE_TTL': 'invalid_number'}):
            config = Config()
            # Should fall back to default
            assert config.CACHE_TTL == 300

    def test_config_performance(self):
        """Test configuration loading performance."""
        import time
        
        start_time = time.time()
        
        # Create multiple config instances
        for _ in range(100):
            config = Config()
            _ = config.DATABASE_URL  # Access a property
        
        end_time = time.time()
        
        # Should be fast (under 0.1 seconds for 100 instances)
        assert (end_time - start_time) < 0.1

    def test_config_thread_safety(self):
        """Test configuration thread safety."""
        import threading
        
        results = []
        
        def get_config_thread():
            config = get_config()
            results.append(config.DATABASE_URL)
        
        # Create multiple threads
        threads = []
        for _ in range(10):
            thread = threading.Thread(target=get_config_thread)
            threads.append(thread)
            thread.start()
        
        # Wait for all threads to complete
        for thread in threads:
            thread.join()
        
        # All threads should get the same config instance
        assert len(set(results)) == 1  # All results should be the same

    def test_config_custom_properties(self):
        """Test adding custom properties to config."""
        config = Config()
        
        # Add custom property
        config.CUSTOM_PROPERTY = "custom_value"
        
        assert config.CUSTOM_PROPERTY == "custom_value"
        assert hasattr(config, 'CUSTOM_PROPERTY')

    def test_config_immutable_defaults(self):
        """Test that default values are not modified."""
        config1 = Config()
        original_database_url = config1.DATABASE_URL
        
        # Modify config1
        config1.DATABASE_URL = "modified_url"
        
        # Create new config instance
        config2 = Config()
        
        # config2 should have original default, not modified value
        assert config2.DATABASE_URL == original_database_url
        assert config2.DATABASE_URL != "modified_url"

    def test_config_env_file_priority(self):
        """Test environment variable priority over .env file."""
        env_content = """
        DATABASE_URL=sqlite:///env_file.db
        REDIS_URL=redis://env_file:6379/0
        """
        
        with patch('builtins.open', mock_open(read_data=env_content)):
            with patch('os.path.exists', return_value=True):
                with patch.dict(os.environ, {
                    'DATABASE_URL': 'sqlite:///env_var.db'
                }):
                    config = Config()
                    
                    # Environment variable should take priority
                    assert config.DATABASE_URL == 'sqlite:///env_var.db'
                    # Other values from .env file
                    assert config.REDIS_URL == 'redis://env_file:6379/0'