"""
Test configuration module for HADES tests.

This module provides configuration overrides for testing.
"""
import os
from unittest.mock import patch

# Set environment variables for testing
os.environ["HADES_ENV"] = "test"

# Use SQLite for auth module tests (no external database needed)
os.environ["HADES_MCP__AUTH__DB_TYPE"] = "sqlite"
os.environ["HADES_MCP__AUTH__DB_PATH"] = ":memory:"

# Keep PostgreSQL configuration for tests that might need it
os.environ["HADES_MCP__AUTH__PG_CONFIG__HOST"] = "localhost"
os.environ["HADES_MCP__AUTH__PG_CONFIG__PORT"] = "5432"
os.environ["HADES_MCP__AUTH__PG_CONFIG__USERNAME"] = "postgres"
os.environ["HADES_MCP__AUTH__PG_CONFIG__PASSWORD"] = "postgres"
os.environ["HADES_MCP__AUTH__PG_CONFIG__DATABASE"] = "hades_test"

# Set ArangoDB configuration for tests (will be mocked)
os.environ["HADES_DB__HOST"] = "http://localhost:8529"
os.environ["HADES_DB__USERNAME"] = "root"
os.environ["HADES_DB__PASSWORD"] = "password"
os.environ["HADES_DB__DATABASE"] = "hades_test"

print("Test configuration loaded: Using SQLite for auth testing and mocks for ArangoDB")
