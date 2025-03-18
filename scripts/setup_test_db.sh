#!/bin/bash
# Setup script for HADES test databases
# This script sets up PostgreSQL and ArangoDB for testing

set -e  # Exit on error

echo "Setting up test databases for HADES..."

# PostgreSQL setup
echo "Setting up PostgreSQL test database..."

# Check if PostgreSQL is running
if ! systemctl is-active --quiet postgresql; then
    echo "PostgreSQL is not running. Starting PostgreSQL..."
    sudo systemctl start postgresql
fi

# Create test database and user if they don't exist
sudo -u postgres psql -c "SELECT 1 FROM pg_roles WHERE rolname='hades_test'" | grep -q 1 || \
    sudo -u postgres psql -c "CREATE USER hades_test WITH PASSWORD 'hades_test';"

sudo -u postgres psql -c "SELECT 1 FROM pg_database WHERE datname='hades_test'" | grep -q 1 || \
    sudo -u postgres psql -c "CREATE DATABASE hades_test OWNER hades_test;"

sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE hades_test TO hades_test;"

echo "PostgreSQL test database setup complete."

# ArangoDB setup
echo "Setting up ArangoDB test database..."

# Check if ArangoDB is installed
if ! command -v arangod &> /dev/null; then
    echo "ArangoDB is not installed. Please install ArangoDB first."
    echo "For Ubuntu: Check installation instructions at https://www.arangodb.com/docs/stable/installation-linux-ubuntu.html"
    echo "You may need to build from source for Noble (24.04): https://github.com/arangodb/arangodb"
    exit 1
else
    echo "ArangoDB is installed."
    
    # Check if ArangoDB service is running
    if ! systemctl is-active --quiet arangodb3; then
        echo "ArangoDB is not running. Starting ArangoDB..."
        sudo systemctl start arangodb3
        sleep 5 # Give it time to start
    fi
    
    echo "ArangoDB service is running."
    
    # Prompt for root password if needed
    echo "Please enter the ArangoDB root password (leave empty if not set):"
    read -s ARANGO_ROOT_PASSWORD
    echo
    
    # Create test database
    echo "Creating ArangoDB test database..."
    if [ -z "$ARANGO_ROOT_PASSWORD" ]; then
        arangosh --server.endpoint tcp://127.0.0.1:8529 --server.username root --server.password "" \
        --javascript.execute-string "db._createDatabase('hades_test'); db._useDatabase('hades_test');"
    else
        arangosh --server.endpoint tcp://127.0.0.1:8529 --server.username root --server.password "$ARANGO_ROOT_PASSWORD" \
        --javascript.execute-string "db._createDatabase('hades_test'); db._useDatabase('hades_test');"
    fi
    
    echo "ArangoDB test database setup complete."
fi

echo "Test database setup complete."
