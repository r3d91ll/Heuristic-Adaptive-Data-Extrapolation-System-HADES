# PostgreSQL Setup Instructions for HADES Testing

These instructions will help you set up the PostgreSQL user and database for HADES testing.

## 1. Create the PostgreSQL User and Database

Run the following commands in your terminal:

```bash
# Copy the SQL file to /tmp where postgres user can access it
cp ~/ML-Lab/Heuristic-Adaptive-Data-Extrapolation-System-HADES/tests/setup_hades_db.sql /tmp/

# Run the SQL setup script as postgres user
sudo -u postgres psql -f /tmp/setup_hades_db.sql

# Clean up
rm /tmp/setup_hades_db.sql
```

This will:
- Create the `hades` PostgreSQL user with password `o$n^3W%QD0HGWxH!`
- Create the `hades_test` database owned by the `hades` user
- Set up the required tables for authentication testing

## 2. Set Up .pgpass File for Authentication

Create or update your `.pgpass` file to store the credentials:

```bash
# Add hades credentials to .pgpass file
echo "localhost:5432:hades_test:hades:o\$n^3W%QD0HGWxH!" >> ~/.pgpass
chmod 600 ~/.pgpass
```

## 3. Verify the PostgreSQL Connection

Run the verification script to check if the connection works:

```bash
cd ~/ML-Lab/Heuristic-Adaptive-Data-Extrapolation-System-HADES
source venv/bin/activate
python tests/verify_pg_connection.py
```

## 4. Run the Tests

If the verification is successful, you can run the tests:

```bash
cd ~/ML-Lab/Heuristic-Adaptive-Data-Extrapolation-System-HADES
./tests/run_pg_tests.sh
```

## Troubleshooting

If you encounter issues with the PostgreSQL connection:

1. Check if the PostgreSQL service is running:
   ```bash
   sudo systemctl status postgresql
   ```

2. If it's not running, start it:
   ```bash
   sudo systemctl start postgresql
   ```

3. Check the PostgreSQL authentication configuration:
   ```bash
   sudo nano /etc/postgresql/*/main/pg_hba.conf
   ```

   Add the following line to allow password authentication for the hades user:
   ```
   host    hades_test    hades    127.0.0.1/32    md5
   ```

4. Restart PostgreSQL after making changes:
   ```bash
   sudo systemctl restart postgresql
   ```
