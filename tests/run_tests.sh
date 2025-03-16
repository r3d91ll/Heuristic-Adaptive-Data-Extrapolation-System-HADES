#!/bin/bash
# Script to run HADES tests with proper database setup

# Set test environment
export HADES_ENV="test"
export ENABLE_AUTH="true"

# Activate virtual environment if it exists
if [ -d ".venv" ]; then
    source .venv/bin/activate
elif [ -d "venv" ]; then
    source venv/bin/activate
fi

# Run the consolidated database setup script first
echo "Setting up test databases..."
python tests/setup_test_databases.py

# If setup was successful, run the tests
if [ $? -eq 0 ]; then
    echo "Running tests..."
    
    # Check if specific tests were provided as arguments
    if [ $# -gt 0 ]; then
        python -m pytest "$@" -v
    else
        # Run all tests by default
        python -m pytest -v
    fi
else
    echo "Database setup failed. Tests will not be run."
    exit 1
fi
