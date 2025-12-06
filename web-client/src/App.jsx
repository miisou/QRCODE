import React, { useState } from 'react';
import VerificationForm from './components/VerificationForm';
import QRCodeDisplay from './components/QRCodeDisplay';
import { initSession } from './services/api';
import './App.css';

function App() {
  const [session, setSession] = useState(null);
  const [loading, setLoading] = useState(false);

  const handleGenerate = async (url) => {
    setLoading(true);
    try {
      const data = await initSession(url);
      setSession(data);
    } catch (error) {
      alert("Error initializing session");
    } finally {
      setLoading(false);
    }
  };

  const handleExpire = () => {
    setSession(null);
    alert("Session expired. Please try again.");
  };

  return (
    <div className="container">
      <header>
        <h1>GovVerify MVP</h1>
      </header>
      <main>
        {!session ? (
          <VerificationForm onGenerate={handleGenerate} />
        ) : (
          <QRCodeDisplay

            // Actually Mobile client manually enters token or scans?
            // Plan: "WC renders QR containing xyz" (nonce) or full payload.
            // Plan Step 1: "qr_payload: myapp://verify?token=a1b2..."
            // Plan Step 2: "Please enter token manually... user enters xyz".
            // If scanning, full payload is better. If manual entry, just nonce.
            // Let's display Nonce text AND QR of payload.
            // Pass session.qr_payload to QR, session.nonce to display text.
            value={session.qr_payload}
            initialTtl={session.expires_in}
            onExpire={handleExpire}
          />
        )}
        {session && (
          <div style={{ marginTop: '20px', textAlign: 'center' }}>
            <p><strong>Token:</strong> {session.nonce}</p>
          </div>
        )}
      </main>
    </div>
  );
}

export default App;
