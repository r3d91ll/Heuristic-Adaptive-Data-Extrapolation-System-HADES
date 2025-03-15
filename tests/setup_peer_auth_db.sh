#!/bin/bash
# Setup script for PostgreSQL database using peer authentication
# This script uses the current system user for PostgreSQL authentication

echo "Setting up PostgreSQL database for HADES testing using peer authentication..."

# Load environment variables from .env.test file
if [ -f ".env.test" ]; then
    echo "Loading PostgreSQL credentials from .env.test file..."
    source .env.test
else
    echo "Warning: .env.test file not found. Using default credentials."
    HADES_TEST_DB_NAME="hades_test"
    HADES_TEST_DB_USER="$USER"
fi

echo "PostgreSQL setup parameters:"
echo "  User: $HADES_TEST_DB_USER (using peer authentication)"
echo "  Database: $HADES_TEST_DB_NAME"

# Create the test database if it doesn't exist
echo "Creating PostgreSQL database '$HADES_TEST_DB_NAME'..."
createdb "$HADES_TEST_DB_NAME" 2>/dev/null || echo "Database '$HADES_TEST_DB_NAME' already exists."

# Create tables for authentication
echo "Creating tables for authentication in '$HADES_TEST_DB_NAME' database..."
psql -d "$HADES_TEST_DB_NAME" -c "
CREATE TABLE IF NOT EXISTS api_keys (
    key_id VARCHAR(64) PRIMARY KEY,
    key_hash VARCHAR(128) NOT NULL,
    name VARCHAR(255) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    last_used TIMESTAMP WITH TIME ZONE
);

CREATE TABLE IF NOT EXISTS rate_limits (
    key_id VARCHAR(64) REFERENCES api_keys(key_id),
    endpoint VARCHAR(255) NOT NULL,
    count INTEGER NOT NULL DEFAULT 0,
    window_start TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (key_id, endpoint)
);"

# Check if the command was successful
if [ $? -ne 0 ]; then
    echo "Failed to create tables. Please check your PostgreSQL installation."
    exit 1
fi

echo "PostgreSQL setup completed successfully!"
echo "User '$HADES_TEST_DB_USER' and database '$HADES_TEST_DB_NAME' are ready for testing."
echo "Using peer authentication (no password required)."

exit 0
