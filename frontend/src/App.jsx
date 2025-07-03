import React, { useEffect, useState } from 'react';
import { Button } from 'shadcn-ui';

function App() {
  const [message, setMessage] = useState('');

  useEffect(() => {
    fetch('/api/ping')
      .then(res => res.json())
      .then(data => setMessage(data.message))
      .catch(() => setMessage('API not available'));
  }, []);

  return (
    <div style={{ padding: 20 }}>
      <h1>FAM Explorer React</h1>
      <p>{message}</p>
      <Button onClick={() => alert('Placeholder')}>Example Button</Button>
    </div>
  );
}

export default App;
