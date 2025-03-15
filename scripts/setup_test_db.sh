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
    echo "For Ubuntu Noble, you might need to use Docker for ArangoDB."
    
    # Check if Docker is installed
    if command -v docker &> /dev/null; then
        echo "Docker is installed. Would you like to run ArangoDB in Docker? (y/n)"
        read -r use_docker
        
        if [ "$use_docker" = "y" ]; then
            # Check if ArangoDB container is already running
            if ! docker ps | grep -q arangodb; then
                echo "Starting ArangoDB in Docker..."
                docker run -d --name arangodb -p 8529:8529 -e ARANGO_ROOT_PASSWORD=password arangodb/arangodb:latest
                
                # Wait for ArangoDB to start
                echo "Waiting for ArangoDB to start..."
                sleep 10
            fi
            
            # Create test database
            echo "Creating ArangoDB test database..."
            docker exec arangodb arangosh --server.endpoint tcp://127.0.0.1:8529 --server.username root --server.password password --javascript.execute-string "db._createDatabase('hades_test'); db._useDatabase('hades_test');"
            
            echo "ArangoDB test database setup complete."
        else
            echo "Skipping ArangoDB setup."
        fi
    else
        echo "Docker is not installed. Please install Docker or ArangoDB first."
    fi
else
    # ArangoDB is installed natively
    echo "ArangoDB is installed. Creating test database..."
    
    # Create test database
    arangosh --server.endpoint tcp://127.0.0.1:8529 --server.username root --server.password "" --javascript.execute-string "db._createDatabase('hades_test'); db._useDatabase('hades_test');"
    
    echo "ArangoDB test database setup complete."
fi

echo "Test database setup complete."
