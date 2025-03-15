# PostgreSQL Migration Guide

This document provides information about the PostgreSQL support added to the HADES authentication system and how to migrate from SQLite to PostgreSQL.

## Overview

The HADES authentication system now supports both SQLite and PostgreSQL as database backends:

- **SQLite**: Suitable for development, testing, and small deployments
- **PostgreSQL**: Recommended for production environments, offering better performance, scalability, and security

## Configuration

### Environment Variables

To configure PostgreSQL, set the following environment variables:

```bash
# Set database type to PostgreSQL
export HADES_MCP__AUTH__DB_TYPE=postgresql

# PostgreSQL connection parameters
export HADES_PG_HOST=localhost
export HADES_PG_PORT=5432
export HADES_PG_USER=hades
export HADES_PG_PASSWORD=your_secure_password
export HADES_PG_DATABASE=hades_auth
```

### Configuration in Code

The configuration is handled by the `PostgreSQLConfig` class in `src/utils/config.py`:

```python
class PostgreSQLConfig(BaseModel):
    """PostgreSQL configuration."""
    host: str = Field(default="localhost")
    port: int = Field(default=5432)
    username: str = Field(default="hades")
    password: str = Field(default="")
    database: str = Field(default="hades_auth")
```

## Migration from SQLite to PostgreSQL

A migration script is provided to help transition from SQLite to PostgreSQL. The script:

1. Creates the necessary PostgreSQL database and tables
2. Migrates existing data from SQLite to PostgreSQL
3. Validates the migration was successful

### Prerequisites

- PostgreSQL server installed and running
- `psycopg2-binary` Python package installed
- Appropriate PostgreSQL user with permissions to create databases and tables

### Running the Migration

```bash
# Set PostgreSQL connection parameters
export HADES_PG_HOST=localhost
export HADES_PG_PORT=5432
export HADES_PG_USER=postgres
export HADES_PG_PASSWORD=your_postgres_password
export HADES_PG_DATABASE=hades_auth

# Run the migration script
python -m src.mcp.migrate_to_postgresql --create-db
```

### Migration Script Options

```
usage: migrate_to_postgresql.py [-h] [--sqlite-path SQLITE_PATH] [--pg-host PG_HOST]
                               [--pg-port PG_PORT] [--pg-user PG_USER]
                               [--pg-password PG_PASSWORD] [--pg-database PG_DATABASE]
                               [--create-db] [--force]

Migrate authentication data from SQLite to PostgreSQL

options:
  -h, --help            show this help message and exit
  --sqlite-path SQLITE_PATH
                        Path to SQLite database file (default: from config)
  --pg-host PG_HOST     PostgreSQL host (default: from config)
  --pg-port PG_PORT     PostgreSQL port (default: from config)
  --pg-user PG_USER     PostgreSQL username (default: from config)
  --pg-password PG_PASSWORD
                        PostgreSQL password (default: from config)
  --pg-database PG_DATABASE
                        PostgreSQL database name (default: from config)
  --create-db           Create the PostgreSQL database if it doesn't exist
  --force               Force migration even if target tables already have data
```

## Testing PostgreSQL Support

A dedicated test file `tests/mcp/test_auth_postgresql.py` is provided to test the PostgreSQL authentication functionality. To run the tests:

```bash
# Set test PostgreSQL connection parameters
export HADES_TEST_PG_HOST=localhost
export HADES_TEST_PG_PORT=5432
export HADES_TEST_PG_USER=postgres
export HADES_TEST_PG_PASSWORD=postgres
export HADES_TEST_PG_DATABASE=hades_test

# Run the tests
python -m unittest tests.mcp.test_auth_postgresql
```

## Implementation Details

The authentication system has been refactored to support both SQLite and PostgreSQL:

1. The `AuthDB` class now dynamically selects the appropriate database type based on configuration
2. A context manager for database connections handles the differences between SQLite and PostgreSQL
3. SQL queries have been updated to use parameterized queries appropriate for each database type:
   - SQLite uses `?` placeholders
   - PostgreSQL uses `%s` placeholders
4. Date handling has been updated to account for differences between SQLite and PostgreSQL:
   - SQLite stores dates as ISO format strings
   - PostgreSQL stores dates as native datetime objects

## Security Considerations

When using PostgreSQL:

1. Use a strong password for the PostgreSQL user
2. Consider using SSL connections for remote PostgreSQL servers
3. Restrict network access to the PostgreSQL server
4. Create a dedicated PostgreSQL user for HADES with minimal permissions
5. Regularly backup the PostgreSQL database

## Troubleshooting

### Connection Issues

If you encounter connection issues:

1. Verify PostgreSQL is running: `pg_isready -h localhost -p 5432`
2. Check PostgreSQL logs: `tail -f /var/log/postgresql/postgresql-*.log`
3. Verify connection parameters are correct
4. Ensure the PostgreSQL user has appropriate permissions

### Migration Issues

If the migration fails:

1. Check if the SQLite database exists and is accessible
2. Verify PostgreSQL connection parameters
3. Ensure the PostgreSQL user has permissions to create tables
4. Check for any error messages in the logs
