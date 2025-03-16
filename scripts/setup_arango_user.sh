#!/bin/bash
# Setup script for ArangoDB user for HADES
# This script creates a 'hades' user in ArangoDB with proper permissions

set -e  # Exit on error

echo "Setting up ArangoDB user for HADES..."

# Check if ArangoDB is running
if ! systemctl is-active --quiet arangodb3; then
    echo "ArangoDB is not running. Starting ArangoDB..."
    sudo systemctl start arangodb3
fi

# Database name
DB_NAME="hades_test"
# User credentials - using same as PostgreSQL for consistency
ARANGO_USER="hades"
ARANGO_PASSWORD="o\$n^3W%QD0HGWxH!"

# Check if the database exists, create if not
echo "Checking if database '$DB_NAME' exists..."
if ! arangosh \
    --server.endpoint tcp://127.0.0.1:8529 \
    --server.username root \
    --server.password "" \
    --javascript.execute-string "db._databases()" | grep -q "$DB_NAME"; then
    
    echo "Creating database '$DB_NAME'..."
    arangosh \
        --server.endpoint tcp://127.0.0.1:8529 \
        --server.username root \
        --server.password "" \
        --javascript.execute-string "db._createDatabase('$DB_NAME')"
fi

# Create user and grant permissions
echo "Creating user '$ARANGO_USER' and granting permissions..."
arangosh \
    --server.endpoint tcp://127.0.0.1:8529 \
    --server.username root \
    --server.password "" \
    --javascript.execute-string "
        try {
            // Check if user exists
            var users = require('@arangodb/users');
            if (!users.exists('$ARANGO_USER')) {
                // Create user
                users.save('$ARANGO_USER', '$ARANGO_PASSWORD');
                console.log('User $ARANGO_USER created successfully');
            } else {
                // Update password if user exists
                users.update('$ARANGO_USER', '$ARANGO_PASSWORD');
                console.log('User $ARANGO_USER already exists, password updated');
            }
            
            // Grant permissions to database
            users.grantDatabase('$ARANGO_USER', '$DB_NAME', 'rw');
            console.log('Granted rw permissions on $DB_NAME to $ARANGO_USER');
            
            // Set up initial collections if needed
            db._useDatabase('$DB_NAME');
            
            // Create document collections if they don't exist
            if (!db._collection('entities')) {
                db._createDocumentCollection('entities');
                console.log('Created entities collection');
            }
            
            if (!db._collection('contexts')) {
                db._createDocumentCollection('contexts');
                console.log('Created contexts collection');
            }
            
            if (!db._collection('domains')) {
                db._createDocumentCollection('domains');
                console.log('Created domains collection');
            }
            
            if (!db._collection('versions')) {
                db._createDocumentCollection('versions');
                console.log('Created versions collection');
            }
            
            if (!db._collection('changes')) {
                db._createDocumentCollection('changes');
                console.log('Created changes collection');
            }
            
            // Create edge collections for relationships
            if (!db._collection('relationships')) {
                db._createEdgeCollection('relationships');
                console.log('Created relationships edge collection');
            }
            
            if (!db._collection('entity_domains')) {
                db._createEdgeCollection('entity_domains');
                console.log('Created entity_domains edge collection');
            }
            
            if (!db._collection('entity_contexts')) {
                db._createEdgeCollection('entity_contexts');
                console.log('Created entity_contexts edge collection');
            }
            
            // Create indexes
            db.entities.ensureIndex({ type: 'persistent', fields: ['name', 'type'] });
            db.entities.ensureIndex({ type: 'persistent', fields: ['version'] });
            db.relationships.ensureIndex({ type: 'persistent', fields: ['_from', '_to', 'type'] });
            db.relationships.ensureIndex({ type: 'persistent', fields: ['version'] });
            db.contexts.ensureIndex({ type: 'fulltext', fields: ['text'] });
            db.changes.ensureIndex({ type: 'persistent', fields: ['document_id', 'version'] });
            
            console.log('Created indexes for collections');
            
        } catch (e) {
            console.error('Error setting up ArangoDB: ' + e.message);
            throw e;
        }
    "

# Verify the user has proper access
echo "Verifying user access..."
arangosh \
    --server.endpoint tcp://127.0.0.1:8529 \
    --server.username "$ARANGO_USER" \
    --server.password "$ARANGO_PASSWORD" \
    --server.database "$DB_NAME" \
    --javascript.execute-string "
        console.log('Successfully connected as $ARANGO_USER to database $DB_NAME');
        console.log('Available collections:');
        db._collections().forEach(function(col) {
            console.log(' - ' + col.name());
        });
    "

echo "ArangoDB user setup complete."
