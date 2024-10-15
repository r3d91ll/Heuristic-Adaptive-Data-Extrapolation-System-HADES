export const processQuery = async (query: string): Promise<string> => {
  try {
    const response = await fetch('http://localhost:3000/query', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ query }),
    });

    if (!response.ok) {
      throw new Error('Network response was not ok');
    }

    const data = await response.json();
    return JSON.stringify(data.result, null, 2);
  } catch (error) {
    console.error('Error:', error);
    return 'An error occurred while processing the query';
  }
};