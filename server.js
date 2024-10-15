const express = require('express');
const cors = require('cors');
const { MilvusClient } = require('@zilliz/milvus2-sdk-node');
const neo4j = require('neo4j-driver');

const app = express();
app.use(cors());
app.use(express.json());

// Milvus client setup
const milvusClient = new MilvusClient('milvus:19530');

// Neo4j driver setup
const neo4jDriver = neo4j.driver(
  'bolt://neo4j:7687',
  neo4j.auth.basic('neo4j', 'password')
);

app.post('/query', async (req, res) => {
  const { query } = req.body;

  try {
    let result;

    if (query.toLowerCase().includes('milvus')) {
      // Simulated Milvus query
      result = await milvusClient.search({
        collection_name: 'example_collection',
        vector: [0.1, 0.2, 0.3], // Example vector
        limit: 5,
      });
    } else if (query.toLowerCase().includes('neo4j')) {
      // Simulated Neo4j query
      const session = neo4jDriver.session();
      const neo4jResult = await session.run(
        'MATCH (n) RETURN n LIMIT 5'
      );
      result = neo4jResult.records.map(record => record.get('n').properties);
      await session.close();
    } else {
      // Simulated code generation
      result = `function processQuery(query) {\n  // TODO: Implement query processing\n  return query.toUpperCase();\n}`;
    }

    res.json({ result });
  } catch (error) {
    console.error('Error processing query:', error);
    res.status(500).json({ error: 'An error occurred while processing the query' });
  }
});

const PORT = process.env.PORT || 3000;
app.listen(PORT, () => {
  console.log(`Server running on port ${PORT}`);
});