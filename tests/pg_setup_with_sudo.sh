#!/bin/bash
# PostgreSQL setup script using sudo for HADES testing

echo "Setting up PostgreSQL database for HADES testing..."

# Copy the SQL file to /tmp where postgres user can access it
cp tests/setup_hades_db.sql /tmp/

# Run the SQL setup script as postgres user
echo "Running PostgreSQL setup script as postgres user..."
sudo -u postgres psql -f /tmp/setup_hades_db.sql

# Check if the command was successful
if [ $? -ne 0 ]; then
    echo "Failed to run PostgreSQL setup script."
    exit 1
fi

# Clean up
rm /tmp/setup_hades_db.sql

# Create a .pgpass file for the hades user
echo "Setting up .pgpass file for authentication..."
if [ ! -f ~/.pgpass ] || ! grep -q "localhost:5432:hades_test:hades:" ~/.pgpass; then
    echo "localhost:5432:hades_test:hades:o\$n^3W%QD0HGWxH!" >> ~/.pgpass
    chmod 600 ~/.pgpass
    echo "Added hades credentials to ~/.pgpass file."
fi

echo "PostgreSQL setup completed successfully!"
echo "You can now run the tests with: ./tests/run_pg_tests.sh"

exit 0
