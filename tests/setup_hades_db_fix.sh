#!/bin/bash
# Fixed setup script for creating the hades database and tables
# This script requires sudo privileges

echo "Setting up hades database and tables..."

# Check if running with sudo
if [ "$EUID" -ne 0 ]; then
    echo "This script must be run with sudo privileges."
    echo "Please run: sudo ./setup_hades_db_fix.sh"
    exit 1
fi

# Create the hades_test database if it doesn't exist
echo "Creating PostgreSQL database 'hades_test'..."
su - postgres -c "psql -c \"CREATE DATABASE hades_test OWNER hades;\""

# Create the tables in the hades_test database
echo "Creating tables in 'hades_test' database..."
su - postgres -c "psql -d hades_test -c \"
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
);

GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO hades;
\""

echo "Database setup completed successfully!"
echo "The hades_test database has been created and configured."
echo ""
echo "You can now run the tests with: ./tests/run_pg_tests.sh"

exit 0
