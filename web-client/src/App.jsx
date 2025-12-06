import React, { useState, useEffect } from 'react';
import VerificationForm from './components/VerificationForm';
import QRCodeDisplay from './components/QRCodeDisplay';
import { initSession, pollSession } from './services/api';
import './App.css';

function App() {
  const [session, setSession] = useState(null);
  const [loading, setLoading] = useState(false);

  const handleGenerate = async () => {
    setLoading(true);
    setExpirationMessage(null);
    try {
      const data = await initSession();
      setSession(data);
    } catch (error) {
      alert("Error initializing session");
    } finally {
      setLoading(false);
    }
  };
  const [expirationMessage, setExpirationMessage] = useState(null);

  const handleExpire = () => {
    setSession(null);
    setExpirationMessage("Token expired");
  };

  useEffect(() => {
    let interval;
    if (session && !session.result && !expirationMessage) {
      interval = setInterval(async () => {
        try {
          const data = await pollSession(session.nonce);
          if (data.status === 'CONSUMED' && data.result) {
            setSession(prev => ({ ...prev, result: data.result }));
            clearInterval(interval);
          } else if (data.status === 'EXPIRED') {
            handleExpire();
            clearInterval(interval);
          }
        } catch (e) {
          console.error("Polling error", e);
        }
      }, 2000);
    }
    return () => clearInterval(interval);
  }, [session, expirationMessage]);

  return (
    <div className="container">
      <header>
        <h1>GovVerify MVP</h1>
      </header>
      <main>
        {!session ? (
          <VerificationForm
            onGenerate={handleGenerate}
            expirationMessage={expirationMessage}
          />
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

        {session && session.result && (
          <div style={{
            marginTop: '20px', padding: '15px', borderRadius: '8px',
            backgroundColor: session.result.verdict === 'TRUSTED' ? '#d4edda' : '#f8d7da',
            color: session.result.verdict === 'TRUSTED' ? '#155724' : '#721c24',
            border: `1px solid ${session.result.verdict === 'TRUSTED' ? '#c3e6cb' : '#f5c6cb'}`
          }}>
            <h2>Verification Result: {session.result.verdict}</h2>
            <p>Trust Score: <strong>{session.result.trust_score}/100</strong></p>
            {session.result.verdict !== 'TRUSTED' && (
              <div>
                <h4>Issues:</h4>
                <ul>
                  {session.result.logs.filter(log => !log.includes("PASS")).map((log, i) => (
                    <li key={i}>{log}</li>
                  ))}
                </ul>
              </div>
            )}
          </div>
        )}
      </main>
    </div>
  );
}

export default App;
