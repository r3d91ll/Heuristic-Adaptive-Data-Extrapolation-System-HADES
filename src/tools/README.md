# HADES Installation Tools

This directory contains scripts for setting up the HADES development environment, including database services (PostgreSQL and ArangoDB).

## Available Scripts

### 1. Native Installation (`install_services.sh`)

This script installs and configures PostgreSQL and ArangoDB directly on your system.

**Features:**
- Installs PostgreSQL and ArangoDB services
- Creates database users and databases
- Sets up proper permissions
- Creates a `.env` file with environment variables
- Runs connection tests to verify the setup

**Usage:**
```bash
# Make the script executable
chmod +x install_services.sh

# Run the installation
./install_services.sh
```

### 2. Docker Development Environment (`docker_dev_environment.sh`)

This script sets up a Docker-based development environment with PostgreSQL and ArangoDB containers.

**Features:**
- Creates a Docker Compose configuration
- Starts PostgreSQL and ArangoDB containers
- Configures database users and permissions
- Creates a `.env.docker` file with environment variables
- Provides commands for managing the environment

**Usage:**
```bash
# Make the script executable
chmod +x docker_dev_environment.sh

# Show help and available options
./docker_dev_environment.sh --help

# Setup and start containers with default settings
./docker_dev_environment.sh

# Start containers only
./docker_dev_environment.sh --start

# Run database connection tests
./docker_dev_environment.sh --test

# Stop and remove containers
./docker_dev_environment.sh --down

# Custom configuration
./docker_dev_environment.sh --postgres-pass secure123 --arango-pass secure456
```

## Environment Variables

Both scripts create environment variable files (`.env` or `.env.docker`) with the following variables:

### PostgreSQL Configuration
- `HADES_MCP__AUTH__DB_TYPE`: Database type (set to `postgresql`)
- `HADES_PG_HOST`: PostgreSQL host
- `HADES_PG_PORT`: PostgreSQL port
- `HADES_PG_USER`: PostgreSQL username
- `HADES_PG_PASSWORD`: PostgreSQL password
- `HADES_PG_DATABASE`: PostgreSQL database name

### ArangoDB Configuration
- `HADES_ARANGO_HOST`: ArangoDB host
- `HADES_ARANGO_PORT`: ArangoDB port
- `HADES_ARANGO_USER`: ArangoDB username
- `HADES_ARANGO_PASSWORD`: ArangoDB password
- `HADES_ARANGO_DATABASE`: ArangoDB database name

## Testing

Both scripts include Python test scripts to verify database connections:
- `test_db_connections.py` for native installation
- `test_docker_connections.py` for Docker environment

These tests verify that:
1. The databases are accessible with the configured credentials
2. Data can be written and read from both databases

## Troubleshooting

If you encounter issues:

1. Check the log files:
   - `install_services.log` for native installation
   - `docker_dev_environment.log` for Docker environment

2. For Docker issues:
   - Verify Docker is running: `docker info`
   - Check container status: `docker-compose ps`
   - View container logs: `docker-compose logs`

3. For native installation issues:
   - Check PostgreSQL status: `sudo systemctl status postgresql`
   - Check ArangoDB status: `sudo systemctl status arangodb3`
   - View PostgreSQL logs: `sudo tail -f /var/log/postgresql/postgresql-*.log`
   - View ArangoDB logs: `sudo tail -f /var/log/arangodb3/arangod.log`
