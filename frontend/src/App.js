import React, { useState } from 'react';
import './App.css';

const API_BASE = process.env.REACT_APP_API_URL || 'http://localhost:3000/api';

function App() {
  const [file, setFile] = useState(null);
  const [username, setUsername] = useState('');
  const [processing, setProcessing] = useState(false);
  const [results, setResults] = useState(null);
  const [error, setError] = useState(null);

  const handleFileChange = (e) => {
    setFile(e.target.files[0]);
    setError(null);
    setResults(null);
  };

  const handleUpload = async () => {
    if (!file) {
      setError('Please select a file');
      return;
    }

    if (!username || username.trim() === '') {
      setError('Please enter a username');
      return;
    }

    try {
      setProcessing(true);
      setError(null);

      // Read file as base64
      const reader = new FileReader();
      reader.onload = async (e) => {
        const base64 = e.target.result.split(',')[1];
        
        const response = await fetch(`${API_BASE}/upload`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({
            file: base64,
            filename: file.name,
            username: username.trim()
          })
        });

        const uploadData = await response.json();
        
        if (response.ok) {
          // If upload succeeded, automatically trigger processing
          if (uploadData.status === 'uploaded') {
            // Call process endpoint
            try {
              const processResponse = await fetch(`${API_BASE}/process`, {
                method: 'POST',
                headers: {
                  'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                  username: username.trim()
                })
              });
              
              const processData = await processResponse.json();
              
              if (processResponse.ok) {
                setResults(processData);
              } else {
                setError(processData.error || 'Processing failed');
                setResults(uploadData); // Still show upload success
              }
            } catch (processErr) {
              setError(`Processing error: ${processErr.message}`);
              setResults(uploadData); // Still show upload success
            }
          } else {
            // Already processed
            setResults(uploadData);
          }
          setProcessing(false);
        } else {
          setError(uploadData.error || 'Upload failed');
          setProcessing(false);
        }
      };
      
      reader.readAsDataURL(file);
    } catch (err) {
      setError(err.message);
      setProcessing(false);
    }
  };

  return (
    <div className="App">
      <header className="App-header">
        <h1>MindTrace EEG Analysis</h1>
        <p>Upload your EEG CSV file for analysis</p>
      </header>

      <main className="App-main">
        <div className="upload-section">
          <input
            type="text"
            placeholder="Enter your username"
            value={username}
            onChange={(e) => setUsername(e.target.value)}
            disabled={processing}
            style={{ padding: '10px', marginBottom: '10px', width: '100%', borderRadius: '6px', border: '1px solid #ddd' }}
          />
          <input
            type="file"
            accept=".csv"
            onChange={handleFileChange}
            disabled={processing}
          />
          <button
            onClick={handleUpload}
            disabled={!file || !username || processing}
          >
            {processing ? 'Processing...' : 'Upload & Analyze'}
          </button>
        </div>

        {error && (
          <div className="error">
            <strong>Error:</strong> {error}
          </div>
        )}

        {results && (
          <div className="results">
            <h2>Analysis Results</h2>
            <div className="result-section">
              <h3>Summary</h3>
              <p>{results.summary}</p>
            </div>

            {results.validation && (
              <div className="result-section">
                <h3>Validation</h3>
                <pre>{JSON.stringify(results.validation, null, 2)}</pre>
              </div>
            )}

            {results.audio_script && (
              <div className="result-section">
                <h3>Audio Script</h3>
                <p>{results.audio_script}</p>
              </div>
            )}

            <div className="api-info">
              <h3>API Endpoints for External Tools</h3>
              <p>Username: <code>{username}</code></p>
              <ul>
                <li>
                  <strong>GET</strong> <code>{API_BASE}/analyze?username={username}</code>
                </li>
                <li>
                  <strong>GET</strong> <code>{API_BASE}/report?username={username}</code>
                </li>
                <li>
                  <strong>GET</strong> <code>{API_BASE}/download/csv?username={username}</code>
                </li>
              </ul>
            </div>
          </div>
        )}
      </main>
    </div>
  );
}

export default App;

