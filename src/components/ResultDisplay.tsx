import React from 'react';

interface ResultDisplayProps {
  result: string;
  loading: boolean;
}

const ResultDisplay: React.FC<ResultDisplayProps> = ({ result, loading }) => {
  if (loading) {
    return <div className="text-center text-gray-600">Processing your query...</div>;
  }

  if (!result) {
    return null;
  }

  return (
    <div className="bg-gray-100 p-4 rounded-lg">
      <h2 className="text-xl font-semibold mb-2">Result:</h2>
      <pre className="whitespace-pre-wrap text-sm">{result}</pre>
    </div>
  );
};

export default ResultDisplay;