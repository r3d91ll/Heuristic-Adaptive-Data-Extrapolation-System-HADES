# HADES Password Rotation System

This document describes the password rotation system for the HADES project, which maintains consistent credentials across the entire system.

## Overview

The password rotation script provides an automated way to update the 'hades' user password across all components:

1. **OS User**: The local Ubuntu system user
2. **PostgreSQL User**: The database user for authentication storage
3. **ArangoDB User**: The database user for knowledge graph storage
4. **Environment Files**: Updates all relevant .env files with new credentials

This approach ensures security consistency across all system components and enables regular credential rotation as part of security best practices.

## Usage

### Manual Password Rotation

To manually rotate the password:

```bash
# Run with sudo to update OS user password
sudo ./scripts/rotate_hades_password.sh [optional_password]
```

- If no password is provided, a secure random password will be generated
- The script will update all system components with the new password
- The new password will be displayed at the end of the execution

### Automated Password Rotation

For automated rotation (recommended every 90 days):

1. Edit the root crontab:

```bash
sudo crontab -e
```

2. Add a crontab entry to run the script periodically:

```
# Run password rotation at 2 AM on the 1st day of every 3rd month
0 2 1 */3 * /home/todd/ML-Lab/Heuristic-Adaptive-Data-Extrapolation-System-HADES/scripts/rotate_hades_password.sh > /home/todd/ML-Lab/Heuristic-Adaptive-Data-Extrapolation-System-HADES/logs/password_rotation.log 2>&1
```

3. Make sure to create the logs directory if it doesn't exist:

```bash
mkdir -p /home/todd/ML-Lab/Heuristic-Adaptive-Data-Extrapolation-System-HADES/logs
```

## What the Script Does

1. **Password Generation**:
   - If no password is provided, generates a secure 16-character random password
   - Includes uppercase, lowercase, numbers, and special characters

2. **OS User Update**:
   - Updates the system user 'hades' password using `chpasswd`

3. **PostgreSQL Update**:
   - Connects to PostgreSQL as the postgres user
   - Updates the 'hades' database user password
   - Requires PostgreSQL to be running

4. **ArangoDB Update**:
   - Connects to ArangoDB as the root user
   - Updates the 'hades' database user password
   - Requires ArangoDB to be running

5. **Environment Files Update**:
   - Updates passwords in `.env`, `.env.test`, and `example.env`
   - Adds password variables if they don't exist
   - Maintains configuration consistency across the application

## Security Considerations

1. **Password Storage**:
   - The generated password is displayed in the terminal and logged
   - For maximum security, store the password in a secure password manager
   - Consider redirecting output to a secure file when using in production

2. **Privilege Requirements**:
   - Script requires sudo/root privileges to update OS user
   - Make sure appropriate access controls are in place for the script itself

3. **Service Restart**:
   - Some services might need to be restarted to pick up new credentials
   - Application-level components reading from .env files might need restarting

4. **Audit Logging**:
   - Consider enhancing the script to log rotation events to a secure audit log
   - Integration with a SIEM system may be appropriate for production environments

## Troubleshooting

If the script fails:

1. Check that both PostgreSQL and ArangoDB services are running
2. Verify that the current user has sudo permissions
3. Ensure that the paths to .env files are correct
4. Check the rotation log file for specific error messages

## Integration with Other Systems

If additional components are added to HADES that require the 'hades' user credentials, the rotation script should be updated to include them.

Potential extensions:
- Integration with external API keys
- Updating credentials in containerized environments
- Rotating backup encryption keys
- Notification system for password changes
