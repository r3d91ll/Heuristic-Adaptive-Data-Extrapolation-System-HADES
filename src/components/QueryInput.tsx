import React from 'react';
import { Send } from 'lucide-react';

interface QueryInputProps {
  query: string;
  setQuery: (query: string) => void;
  onSubmit: (e: React.FormEvent) => void;
  loading: boolean;
}

const QueryInput: React.FC<QueryInputProps> = ({ query, setQuery, onSubmit, loading }) => {
  return (
    <form onSubmit={onSubmit} className="mb-4">
      <div className="flex items-center border-b border-gray-300 py-2">
        <input
          type="text"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="Enter your query or code snippet..."
          className="appearance-none bg-transparent border-none w-full text-gray-700 mr-3 py-1 px-2 leading-tight focus:outline-none"
        />
        <button
          type="submit"
          disabled={loading}
          className={`flex-shrink-0 bg-blue-500 hover:bg-blue-700 border-blue-500 hover:border-blue-700 text-sm border-4 text-white py-1 px-2 rounded ${
            loading ? 'opacity-50 cursor-not-allowed' : ''
          }`}
        >
          {loading ? 'Processing...' : <Send className="w-4 h-4" />}
        </button>
      </div>
    </form>
  );
};

export default QueryInput;