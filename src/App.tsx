import React, { useState } from 'react';
import { Search, Database, Code2 } from 'lucide-react';
import QueryInput from './components/QueryInput';
import ResultDisplay from './components/ResultDisplay';
import { processQuery } from './utils/queryProcessor';

function App() {
  const [query, setQuery] = useState('');
  const [result, setResult] = useState('');
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    const processedResult = await processQuery(query);
    setResult(processedResult);
    setLoading(false);
  };

  return (
    <div className="min-h-screen bg-gray-100 flex flex-col items-center justify-center p-4">
      <header className="mb-8 text-center">
        <h1 className="text-4xl font-bold text-gray-800 mb-2">HADES</h1>
        <p className="text-xl text-gray-600">Heuristic Adaptive Data Extraction System</p>
      </header>
      <main className="w-full max-w-3xl bg-white rounded-lg shadow-md p-6">
        <QueryInput query={query} setQuery={setQuery} onSubmit={handleSubmit} loading={loading} />
        <ResultDisplay result={result} loading={loading} />
      </main>
      <footer className="mt-8 flex space-x-4">
        <div className="flex items-center text-gray-600">
          <Search className="w-5 h-5 mr-2" />
          <span>Milvus Search</span>
        </div>
        <div className="flex items-center text-gray-600">
          <Database className="w-5 h-5 mr-2" />
          <span>Neo4j Query</span>
        </div>
        <div className="flex items-center text-gray-600">
          <Code2 className="w-5 h-5 mr-2" />
          <span>Code Generation</span>
        </div>
      </footer>
    </div>
  );
}

export default App;