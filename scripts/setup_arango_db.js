// ArangoDB setup script
// This will create the hades user, database, and all necessary collections

try {
  // Check if user exists
  var users = require('@arangodb/users');
  var username = ARGUMENTS[0];
  var password = ARGUMENTS[1];
  var dbName = ARGUMENTS[2];
  
  if (!users.exists(username)) {
    // Create user
    users.save(username, password);
    print('User ' + username + ' created successfully');
  } else {
    // Update password if user exists
    users.update(username, password);
    print('User ' + username + ' already exists, password updated');
  }
  
  // Check if database exists
  if (db._databases().indexOf(dbName) === -1) {
    // Create database
    require('@arangodb/arango-database')._createDatabase(dbName);
    print('Database ' + dbName + ' created');
  } else {
    print('Database ' + dbName + ' already exists');
  }
  
  // Grant RW access to database
  users.grantDatabase(username, dbName, 'rw');
  print('Granted RW permissions on ' + dbName + ' to ' + username);
  
  // Switch to the database and create collections
  db._useDatabase(dbName);
  
  // Create document collections
  var documentCollections = [
    'entities', 
    'contexts', 
    'domains', 
    'versions', 
    'changes'
  ];
  
  documentCollections.forEach(function(col) {
    if (!db._collection(col)) {
      db._createDocumentCollection(col);
      print('Created ' + col + ' collection');
    } else {
      print('Collection ' + col + ' already exists');
    }
  });
  
  // Create edge collections
  var edgeCollections = [
    'relationships', 
    'entity_domains', 
    'entity_contexts'
  ];
  
  edgeCollections.forEach(function(col) {
    if (!db._collection(col)) {
      db._createEdgeCollection(col);
      print('Created ' + col + ' edge collection');
    } else {
      print('Collection ' + col + ' already exists');
    }
  });
  
  // Create indexes
  db.entities.ensureIndex({ type: 'persistent', fields: ['name', 'type'] });
  db.entities.ensureIndex({ type: 'persistent', fields: ['version'] });
  db.relationships.ensureIndex({ type: 'persistent', fields: ['_from', '_to', 'type'] });
  db.relationships.ensureIndex({ type: 'persistent', fields: ['version'] });
  db.contexts.ensureIndex({ type: 'fulltext', fields: ['text'] });
  db.changes.ensureIndex({ type: 'persistent', fields: ['document_id', 'version'] });
  
  print('Created indexes for collections');
  
  // Give the user admin rights on the database
  users.grantDatabase(username, dbName, 'rw');
  
  // Grant collection access
  var allCollections = documentCollections.concat(edgeCollections);
  allCollections.forEach(function(col) {
    users.grantCollection(username, dbName, col, 'rw');
    print('Granted RW access on collection ' + col + ' to ' + username);
  });
  
  print('ArangoDB user setup complete');
} catch (e) {
  print('Error setting up ArangoDB: ' + e.message);
  throw e;
}
