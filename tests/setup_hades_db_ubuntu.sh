#!/bin/bash
# Setup script for PostgreSQL hades database on Ubuntu
# This script uses sudo -u postgres to create the hades user and database

# Load environment variables from .env.test file
if [ -f ".env.test" ]; then
    echo "Loading PostgreSQL credentials from .env.test file..."
    source .env.test
else
    echo "Warning: .env.test file not found. Using default credentials."
    HADES_TEST_DB_NAME="hades_test"
    HADES_TEST_DB_USER="hades"
    HADES_TEST_DB_PASSWORD="o\$n^3W%QD0HGWxH!"
fi

echo "Setting up PostgreSQL database for HADES..."
echo "  User: $HADES_TEST_DB_USER"
echo "  Database: $HADES_TEST_DB_NAME"
echo "  Password: [provided]"

# Create the hades user if it doesn't exist
echo "Creating PostgreSQL user '$HADES_TEST_DB_USER'..."
sudo -u postgres psql -c "DO \$\$
BEGIN
    IF NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = '$HADES_TEST_DB_USER') THEN
        CREATE USER $HADES_TEST_DB_USER WITH PASSWORD '$HADES_TEST_DB_PASSWORD';
        ALTER USER $HADES_TEST_DB_USER CREATEDB;
    ELSE
        ALTER USER $HADES_TEST_DB_USER WITH PASSWORD '$HADES_TEST_DB_PASSWORD';
    END IF;
END
\$\$;"

# Check if the command was successful
if [ $? -ne 0 ]; then
    echo "Failed to create PostgreSQL user. Please check your sudo privileges."
    exit 1
fi

# Create the hades_test database if it doesn't exist
echo "Creating PostgreSQL database '$HADES_TEST_DB_NAME'..."
sudo -u postgres psql -c "SELECT 'CREATE DATABASE $HADES_TEST_DB_NAME OWNER $HADES_TEST_DB_USER' WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = '$HADES_TEST_DB_NAME')\gexec"

# Check if the command was successful
if [ $? -ne 0 ]; then
    echo "Failed to create PostgreSQL database. Please check your sudo privileges."
    exit 1
fi

# Create the tables in the hades_test database
echo "Creating tables in '$HADES_TEST_DB_NAME' database..."
sudo -u postgres psql -d $HADES_TEST_DB_NAME -c "
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

GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO $HADES_TEST_DB_USER;
"

# Check if the command was successful
if [ $? -ne 0 ]; then
    echo "Failed to create tables. Please check your PostgreSQL installation."
    exit 1
fi

echo "PostgreSQL setup completed successfully!"
echo "User '$HADES_TEST_DB_USER' and database '$HADES_TEST_DB_NAME' are ready for testing."

# Update the pg_hba.conf file to allow password authentication for the hades user
echo "You may need to update your pg_hba.conf file to allow password authentication for the $HADES_TEST_DB_USER user."
echo "Add the following line to your pg_hba.conf file:"
echo "host    $HADES_TEST_DB_NAME    $HADES_TEST_DB_USER    127.0.0.1/32    md5"
echo "Then restart PostgreSQL with: sudo systemctl restart postgresql"

exit 0
