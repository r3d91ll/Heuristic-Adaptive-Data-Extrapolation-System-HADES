#!/bin/bash
# Script to run PostgreSQL-based tests with proper credentials

# Load environment variables from .env.test file
if [ -f ".env.test" ]; then
    echo "Loading PostgreSQL credentials from .env.test file..."
    export $(grep -v '^#' .env.test | xargs)
else
    echo "Warning: .env.test file not found. Using default credentials."
    # Set default PostgreSQL credentials for tests
    export HADES_TEST_DB_NAME="hades_test"
    export HADES_TEST_DB_USER="hades"
    export HADES_TEST_DB_PASSWORD="o$n^3W%QD0HGWxH!"  # Default password
    export HADES_TEST_DB_HOST="localhost"
    export HADES_TEST_DB_PORT="5432"
fi

# Set test environment
export HADES_ENV="test"
export ENABLE_AUTH="true"

# Activate virtual environment if it exists
if [ -d "venv" ]; then
    source venv/bin/activate
fi

# Run the peer authentication setup script first
echo "Setting up PostgreSQL test database..."
./tests/setup_peer_auth_db.sh

# If setup was successful, run the tests
if [ $? -eq 0 ]; then
    echo "Running PostgreSQL-based tests..."
    python -m pytest tests/unit/mcp/test_auth_real_db.py -v
else
    echo "Database setup failed. Tests will not be run."
    exit 1
fi
