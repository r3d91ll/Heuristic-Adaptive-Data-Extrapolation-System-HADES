"""
Test configuration module for HADES tests.

This module provides configuration overrides for testing.
"""
import os
import sys
from unittest.mock import patch

# Set environment variables for testing
os.environ["HADES_ENV"] = "test"

# Determine if we should use real database connections
USE_REAL_DB = os.environ.get("HADES_TEST_USE_REAL_DB", "true").lower() in ("true", "1", "yes")

# Use SQLite for auth module tests by default (no external database needed)
os.environ["HADES_MCP__AUTH__DB_TYPE"] = "sqlite"
os.environ["HADES_MCP__AUTH__DB_PATH"] = ":memory:"

# PostgreSQL configuration for tests
if USE_REAL_DB:
    try:
        # Try to import PostgreSQL test parameters
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        from pg_test_env import PG_TEST_PARAMS
        
        os.environ["HADES_MCP__AUTH__PG_CONFIG__HOST"] = PG_TEST_PARAMS["host"]
        os.environ["HADES_MCP__AUTH__PG_CONFIG__PORT"] = PG_TEST_PARAMS["port"]
        os.environ["HADES_MCP__AUTH__PG_CONFIG__USERNAME"] = PG_TEST_PARAMS["user"]
        os.environ["HADES_MCP__AUTH__PG_CONFIG__PASSWORD"] = PG_TEST_PARAMS["password"]
        os.environ["HADES_MCP__AUTH__PG_CONFIG__DATABASE"] = PG_TEST_PARAMS["dbname"]
    except ImportError:
        # Use dedicated 'hades' user for PostgreSQL tests
        os.environ["HADES_MCP__AUTH__PG_CONFIG__HOST"] = "localhost"
        os.environ["HADES_MCP__AUTH__PG_CONFIG__PORT"] = "5432"
        os.environ["HADES_MCP__AUTH__PG_CONFIG__USERNAME"] = "hades"
        os.environ["HADES_MCP__AUTH__PG_CONFIG__PASSWORD"] = "o$n^3W%QD0HGWxH!"
        os.environ["HADES_MCP__AUTH__PG_CONFIG__DATABASE"] = "hades_test"
else:
    # Default PostgreSQL configuration for mocked tests
    os.environ["HADES_MCP__AUTH__PG_CONFIG__HOST"] = "localhost"
    os.environ["HADES_MCP__AUTH__PG_CONFIG__PORT"] = "5432"
    os.environ["HADES_MCP__AUTH__PG_CONFIG__USERNAME"] = "postgres"
    os.environ["HADES_MCP__AUTH__PG_CONFIG__PASSWORD"] = "postgres"
    os.environ["HADES_MCP__AUTH__PG_CONFIG__DATABASE"] = "hades_test"

# ArangoDB configuration for tests
if USE_REAL_DB:
    try:
        # Try to import ArangoDB test parameters
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        from arango_test_env import ARANGO_TEST_PARAMS
        
        os.environ["HADES_DB__HOST"] = ARANGO_TEST_PARAMS["host"]
        os.environ["HADES_DB__USERNAME"] = ARANGO_TEST_PARAMS["username"]
        os.environ["HADES_DB__PASSWORD"] = ARANGO_TEST_PARAMS["password"]
        os.environ["HADES_DB__DATABASE"] = ARANGO_TEST_PARAMS["database"]
    except ImportError:
        # Use dedicated 'hades' user for ArangoDB tests
        os.environ["HADES_DB__HOST"] = "http://localhost:8529"
        os.environ["HADES_DB__USERNAME"] = "hades"
        os.environ["HADES_DB__PASSWORD"] = "dpvL#tocbHQeKBd4"
        os.environ["HADES_DB__DATABASE"] = "hades_graph"
else:
    # Default ArangoDB configuration for mocked tests
    os.environ["HADES_DB__HOST"] = "http://localhost:8529"
    os.environ["HADES_DB__USERNAME"] = "root"
    os.environ["HADES_DB__PASSWORD"] = "password"
    os.environ["HADES_DB__DATABASE"] = "hades_test"

if USE_REAL_DB:
    print("Test configuration loaded: Using real database connections for PostgreSQL and ArangoDB")
else:
    print("Test configuration loaded: Using SQLite for auth testing and mocks for ArangoDB")