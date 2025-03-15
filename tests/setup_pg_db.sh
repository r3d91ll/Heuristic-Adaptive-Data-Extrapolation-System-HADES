#!/bin/bash
# Simplified PostgreSQL setup script for HADES testing
# This script assumes you have the necessary PostgreSQL permissions

echo "Setting up PostgreSQL database for HADES testing..."

# Check if psql is available
if ! command -v psql &> /dev/null; then
    echo "Error: psql command not found. Please make sure PostgreSQL is installed."
    exit 1
fi

# Run the SQL setup script
echo "Running PostgreSQL setup script..."
psql -U postgres -f tests/setup_hades_db.sql

# Check if the command was successful
if [ $? -ne 0 ]; then
    echo "Failed to run PostgreSQL setup script."
    echo "You may need to add your user to the postgres group:"
    echo "  sudo usermod -a -G postgres $USER"
    echo "  newgrp postgres"
    echo "Or run the script manually as the postgres user:"
    echo "  sudo -u postgres psql -f tests/setup_hades_db.sql"
    exit 1
fi

# Update the .pgpass file to store credentials
if [ ! -f ~/.pgpass ] || ! grep -q "localhost:5432:hades_test:hades:" ~/.pgpass; then
    echo "Updating ~/.pgpass file with hades credentials..."
    echo "localhost:5432:hades_test:hades:o\$n^3W%QD0HGWxH!" >> ~/.pgpass
    chmod 600 ~/.pgpass
    echo "Added hades credentials to ~/.pgpass file."
fi

echo "PostgreSQL setup completed successfully!"
echo "You can now run the tests with: ./tests/run_pg_tests.sh"

exit 0
