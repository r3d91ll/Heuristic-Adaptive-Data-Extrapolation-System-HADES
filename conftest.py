import pytest
import os
from unittest.mock import patch

@pytest.fixture(autouse=True)
def mock_env_vars():
    """Automatically mock environment variables for all tests"""
    with patch.dict(os.environ, {}, clear=True):
        yield

@pytest.fixture
def mock_db():
    """Provide a mock database connection"""
    from unittest.mock import MagicMock
    return MagicMock()

@pytest.fixture
def mock_milvus():
    """Provide a mock Milvus connection"""
    from unittest.mock import MagicMock
    return MagicMock()

def pytest_configure(config):
    """Register custom markers."""
    config.addinivalue_line(
        "markers",
        "env_vars(dict): mark test to set environment variables"
    )

@pytest.fixture
def env_setup(monkeypatch):
    """Set up environment variables for a test."""
    def _env_setup(env_vars):
        for key, value in env_vars.items():
            monkeypatch.setenv(key, str(value))
    return _env_setup 