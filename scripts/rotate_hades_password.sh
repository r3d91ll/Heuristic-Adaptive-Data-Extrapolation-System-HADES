#!/bin/bash
# Password Rotation Script for HADES
# This script updates the password for the 'hades' user across all components:
#   - Local OS user
#   - PostgreSQL user
#   - ArangoDB user
#   - Updates .env files
#   - Rotates API keys
#
# This script should be run as root (sudo) or by an administrator with appropriate permissions
# Usage: sudo ./rotate_hades_password.sh [password]
# If no password is provided, a secure random one will be generated.

set -e  # Exit on error

# Check if running with sudo
if [ "$EUID" -ne 0 ]; then
  echo "Please run as root (use sudo)"
  exit 1
fi

# Project root directory
PROJECT_DIR="$(dirname "$(dirname "$(realpath "$0")")")"
echo "Project directory: $PROJECT_DIR"

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Configuration
USER="hades"
PG_DATABASE="hades_auth"  # From .env
ARANGO_DATABASE="hades_graph"  # From .env
ENV_FILES=(
  "$PROJECT_DIR/.env"
  "$PROJECT_DIR/.env.test"
  "$PROJECT_DIR/example.env"
)

# Generate or use provided password
if [ -z "$1" ]; then
  # Generate a secure random password (16 characters with special chars)
  NEW_PASSWORD=$(LC_ALL=C tr -dc 'A-Za-z0-9_!@#$%^&*()-+=' < /dev/urandom | head -c 16)
  echo -e "${YELLOW}Generated new password.${NC}"
else
  NEW_PASSWORD="$1"
  echo -e "${YELLOW}Using provided password.${NC}"
fi

# Generate new API keys
SERVICE_API_KEY=$(LC_ALL=C tr -dc 'a-f0-9' < /dev/urandom | head -c 64)
ADMIN_API_KEY=$(LC_ALL=C tr -dc 'a-f0-9' < /dev/urandom | head -c 64)

echo "Starting password rotation for user '$USER' at $(date)"
echo "--------------------------------------------------------"

# 1. Update the local OS user password
echo -e "${GREEN}[1/4]${NC} Updating OS user password..."
echo "$USER:$NEW_PASSWORD" | chpasswd
if [ $? -eq 0 ]; then
  echo -e "  ${GREEN}✓${NC} OS user password updated successfully."
else
  echo -e "  ${RED}✗${NC} Failed to update OS user password."
  exit 1
fi

# 2. Update PostgreSQL user password
echo -e "${GREEN}[2/4]${NC} Updating PostgreSQL user password..."
if systemctl is-active --quiet postgresql; then
  sudo -u postgres psql -c "ALTER USER $USER WITH PASSWORD '$NEW_PASSWORD';"
  if [ $? -eq 0 ]; then
    echo -e "  ${GREEN}✓${NC} PostgreSQL user password updated successfully."
  else
    echo -e "  ${RED}✗${NC} Failed to update PostgreSQL user password."
    exit 1
  fi
else
  echo -e "  ${RED}✗${NC} PostgreSQL is not running. Cannot update password."
  exit 1
fi

# 3. Update ArangoDB user password
echo -e "${GREEN}[3/4]${NC} Updating ArangoDB user password..."
# Check if ArangoDB is running by trying to connect to it
if curl -s http://localhost:8529/_api/version > /dev/null; then
  # Get current ArangoDB password from .env file
  CURRENT_ARANGO_PASSWORD=""
  if [ -f "$PROJECT_DIR/.env" ]; then
    CURRENT_ARANGO_PASSWORD=$(grep HADES_ARANGO_PASSWORD "$PROJECT_DIR/.env" | cut -d'=' -f2)
  fi
  
  # Escape special characters for JavaScript string
  ESCAPED_PASSWORD=$(echo "$NEW_PASSWORD" | sed 's/[\\\"]/\\&/g')
  
  # Create a temporary JavaScript file for ArangoDB
  TMP_JS_FILE=$(mktemp)
  cat > "$TMP_JS_FILE" <<EOF
  try {
    var users = require('@arangodb/users');
    if (users.exists('$USER')) {
      users.update('$USER', '$ESCAPED_PASSWORD');
      print('User $USER password updated successfully');
    } else {
      print('User $USER does not exist in ArangoDB');
      print('Creating user $USER with password');
      users.save('$USER', '$ESCAPED_PASSWORD');
    }
  } catch (e) {
    print('Error updating ArangoDB user: ' + e.message);
    throw e;
  }
EOF
  
  # First try with the hades user (if we have a current password)
  ARANGO_UPDATED=false
  if [ -n "$CURRENT_ARANGO_PASSWORD" ]; then
    echo -e "  ${YELLOW}!${NC} Attempting to update ArangoDB password using current hades user..."
    arangosh \
      --server.endpoint tcp://127.0.0.1:8529 \
      --server.username "$USER" \
      --server.password "$CURRENT_ARANGO_PASSWORD" \
      --server.database "$ARANGO_DATABASE" \
      --javascript.execute "$TMP_JS_FILE" 2>/dev/null
    
    if [ $? -eq 0 ]; then
      ARANGO_UPDATED=true
      echo -e "  ${GREEN}✓${NC} ArangoDB user password updated successfully."
    else
      echo -e "  ${YELLOW}!${NC} Could not update password as hades user. Trying with root..."
    fi
  fi
  
  # If that failed, try with root (prompt for password)
  if [ "$ARANGO_UPDATED" = false ]; then
    echo -e "  ${YELLOW}!${NC} Please enter the ArangoDB root password:"
    read -s ROOT_PASSWORD
    echo
    
    arangosh \
      --server.endpoint tcp://127.0.0.1:8529 \
      --server.username root \
      --server.password "$ROOT_PASSWORD" \
      --javascript.execute "$TMP_JS_FILE"
    
    if [ $? -eq 0 ]; then
      echo -e "  ${GREEN}✓${NC} ArangoDB user password updated successfully."
    else
      echo -e "  ${RED}✗${NC} Failed to update ArangoDB user password."
      echo -e "  ${YELLOW}!${NC} Continuing with other updates..."
    fi
  fi
  
  # Clean up temp file
  rm "$TMP_JS_FILE"
else
  echo -e "  ${RED}✗${NC} Cannot connect to ArangoDB at http://localhost:8529. Check if it's running."
  echo -e "  ${YELLOW}!${NC} Continuing with other updates..."
fi

# 4. Update .env files and API keys
echo -e "${GREEN}[4/4]${NC} Updating environment files and API keys..."
for env_file in "${ENV_FILES[@]}"; do
  if [ -f "$env_file" ]; then
    # Update PostgreSQL password in env file
    sed -i "s/^HADES_PG_PASSWORD=.*$/HADES_PG_PASSWORD=$NEW_PASSWORD/" "$env_file"
    
    # Update ArangoDB password in env file
    sed -i "s/^HADES_ARANGO_PASSWORD=.*$/HADES_ARANGO_PASSWORD=$NEW_PASSWORD/" "$env_file"
    
    # Update API keys
    sed -i "s/^HADES_SERVICE_API_KEY=.*$/HADES_SERVICE_API_KEY=$SERVICE_API_KEY/" "$env_file"
    sed -i "s/^HADES_ADMIN_API_KEY=.*$/HADES_ADMIN_API_KEY=$ADMIN_API_KEY/" "$env_file"
    
    # If these variables don't exist, add them
    if ! grep -q "HADES_PG_PASSWORD" "$env_file"; then
      echo "HADES_PG_PASSWORD=$NEW_PASSWORD" >> "$env_file"
    fi
    
    if ! grep -q "HADES_ARANGO_PASSWORD" "$env_file"; then
      echo "HADES_ARANGO_PASSWORD=$NEW_PASSWORD" >> "$env_file"
    fi
    
    if ! grep -q "HADES_SERVICE_API_KEY" "$env_file"; then
      echo "HADES_SERVICE_API_KEY=$SERVICE_API_KEY" >> "$env_file"
    fi
    
    if ! grep -q "HADES_ADMIN_API_KEY" "$env_file"; then
      echo "HADES_ADMIN_API_KEY=$ADMIN_API_KEY" >> "$env_file"
    fi
    
    echo -e "  ${GREEN}✓${NC} Updated $env_file"
  else
    echo -e "  ${YELLOW}!${NC} Warning: $env_file not found"
  fi
done

echo "--------------------------------------------------------"
echo -e "${GREEN}Password rotation completed successfully!${NC}"
echo "New password: $NEW_PASSWORD"
echo "New API Keys:"
echo "  Service API Key: $SERVICE_API_KEY"
echo "  Admin API Key: $ADMIN_API_KEY"
echo "Please save these credentials securely and update any additional services that might use them."
echo "--------------------------------------------------------"
echo "Rotation timestamp: $(date)"
echo "Consider scheduling the next rotation with: sudo crontab -e"
echo "Example entry for every 90 days at 2 AM:"
echo "0 2 1 */3 * $PROJECT_DIR/scripts/rotate_hades_password.sh > $PROJECT_DIR/logs/password_rotation.log 2>&1"