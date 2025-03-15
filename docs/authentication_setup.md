# HADES Authentication System Setup

This document outlines the authentication system setup for the HADES project, including the PostgreSQL database configuration, API key management, and integration with FastAPI.

## Overview

The HADES authentication system uses a PostgreSQL database to store and validate API keys, providing secure access to the API endpoints. The system includes:

- A dedicated system user (`hades`) for database management
- A PostgreSQL role with the same name for database authentication
- Tables for storing API keys and rate limiting information
- A FastAPI integration for securing endpoints

## PostgreSQL Setup

### Database Configuration

1. **System User**: A dedicated system user named `hades` has been created to manage the PostgreSQL database.

2. **PostgreSQL Role**: A corresponding PostgreSQL role named `hades` has been created with superuser privileges.

3. **Database**: A database named `hades_test` has been created, owned by the `hades` user.

4. **Tables**:
   - `api_keys`: Stores API key information (ID, hash, name, creation date, last used)
   - `rate_limits`: Tracks rate limiting information for each API key and endpoint

### Authentication Configuration

The PostgreSQL configuration has been updated to allow password authentication for the `hades` user:

```
host    hades_test    hades    127.0.0.1/32    md5
```

## API Key Management

### API Key Structure

Each API key consists of:
- **Key ID**: A unique identifier for the API key (32 hex characters)
- **API Key**: The actual key used for authentication (64 hex characters)
- **Name**: A human-readable name for the key
- **Created At**: Timestamp when the key was created
- **Last Used**: Timestamp when the key was last used

### API Key Storage

API keys are securely stored in the database:
- Only the hash of the API key is stored, not the key itself
- The key ID is used to reference the key in the rate limiting table

### API Key Generation

API keys can be generated using the provided scripts:
- `python -m hades.auth.pg_auth create <name>`: Creates a new API key
- `python -m hades.auth.pg_auth list`: Lists all API keys
- `python -m hades.auth.pg_auth delete <key_id>`: Deletes an API key

Production API keys have been generated and added to the `.env` and `.env.test` files:
- `HADES_SERVICE_API_KEY`: For general service authentication
- `HADES_ADMIN_API_KEY`: For administrative operations

## FastAPI Integration

### Authentication Dependency

The authentication system is integrated with FastAPI using a dependency:

```python
from hades.auth.pg_auth import get_api_key

@app.get("/secure")
async def secure_endpoint(key_info=Depends(get_api_key)):
    return {"message": "Authentication successful"}
```

### Rate Limiting

The authentication system includes rate limiting functionality:
- Each API key has a separate rate limit for each endpoint
- Default rate limit: 100 requests per hour
- Rate limits are tracked in the `rate_limits` table

## Testing

The authentication system has been tested with:
- Connection verification to ensure the database is accessible
- API key creation and validation
- Endpoint security testing
- Rate limiting testing

## Next Steps

1. **Integration Testing**: Test the authentication system with the full HADES API
2. **Load Testing**: Verify the performance under high load
3. **Security Audit**: Review the security of the authentication system
4. **Documentation**: Complete the API documentation with authentication requirements

## References

- [PostgreSQL Documentation](https://www.postgresql.org/docs/)
- [FastAPI Security](https://fastapi.tiangolo.com/tutorial/security/)
- [API Key Best Practices](https://cloud.google.com/endpoints/docs/openapi/when-why-api-key)
