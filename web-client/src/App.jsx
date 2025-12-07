import React, { useState, useEffect } from 'react';
import VerificationForm from './components/VerificationForm';
import QRCodeDisplay from './components/QRCodeDisplay';
import { initSession, pollSession } from './services/api';
// Импортируем сканер и генератор
import { requestDeviceWithUUID, generateBLEUUID } from './services/bluetoothScanner';
import './App.css';

function App() {
  const [session, setSession] = useState(null);
  const [loading, setLoading] = useState(false);

  // Состояния для BLE
  const [bleStatus, setBleStatus] = useState(null);
  const [bleUUID, setBleUUID] = useState(null); // Храним UUID текущей сессии
  const [deviceName, setDeviceName] = useState(null);

  const [expirationMessage, setExpirationMessage] = useState(null);

  const handleGenerate = async () => {
    setLoading(true);
    setExpirationMessage(null);
    setBleStatus(null);
    setDeviceName(null);

    // 1. Генерируем UUID для этой сессии
    const newBleUUID = generateBLEUUID();
    setBleUUID(newBleUUID);

    try {
      const data = await initSession();

      // 2. Добавляем UUID в QR payload, чтобы телефон мог его прочитать и начать вещать
      const updatedData = {
        ...data,
        qr_payload: `${data.qr_payload}&uuid=${newBleUUID}`
      };

      setSession(updatedData);
    } catch (error) {
      alert("Error initializing session");
    } finally {
      setLoading(false);
    }
  };

  // Ручной запуск сканирования с фильтром по UUID
  const handleManualScan = async () => {
    if (!bleUUID) return; // Если UUID нет, сканировать нечего

    setBleStatus('scanning');

    // Передаем конкретный UUID в фильтр
    const result = await requestDeviceWithUUID(bleUUID);

    if (result.found) {
      setBleStatus('found');
      setDeviceName(result.name);
    } else if (result.error === 'Bluetooth not supported in this browser') {
      setBleStatus('not_supported');
    } else {
      // Скорее всего пользователь не нашел устройство в списке и закрыл окно
      setBleStatus('not_found');
    }
  };

  const handleExpire = () => {
    setSession(null);
    setExpirationMessage("Token expired");
    setBleStatus(null);
    setBleUUID(null);
  };

  // (useEffect для поллинга остался без изменений...)
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
      <header><h1>GovVerify</h1></header>
      <main>
        {!session ? (
          <VerificationForm
            onGenerate={handleGenerate}
            expirationMessage={expirationMessage}
            isLoading={loading}
          />
        ) : (
          <>
            <QRCodeDisplay
              value={session.qr_payload}
              initialTtl={session.expires_in}
              onExpire={handleExpire}
            />

            <div style={{ textAlign: 'center', marginTop: '10px', color: '#666' }}>
              <small>Session UUID: {bleUUID}</small>
            </div>

            {/* Блок с токеном (как раньше) ... */}
            <div style={{ marginTop: '20px', padding: '15px', backgroundColor: '#f5f5f5', borderRadius: '8px', textAlign: 'center' }}>
              <p style={{ margin: '0 0 10px 0', fontWeight: 'bold' }}>Token (Nonce):</p>
              <code style={{ padding: '8px 12px', backgroundColor: '#fff', border: '1px solid #ddd', borderRadius: '4px', fontFamily: 'monospace' }}>
                {session.nonce}
              </code>
            </div>



            <div style={{ marginTop: '20px', textAlign: 'center' }}>

              {!bleStatus || bleStatus === 'not_found' || bleStatus === 'canceled' ? (

                <button
                  onClick={handleManualScan}
                  style={{
                    padding: '15px 30px',
                    backgroundColor: '#28a745',
                    color: 'white',
                    border: 'none',
                    borderRadius: '8px',
                    fontSize: '18px',
                    fontWeight: 'bold',
                    cursor: 'pointer',
                    boxShadow: '0 4px 6px rgba(0,0,0,0.1)',
                  }}
                >
                  📡 Find device
                </button>

              ) : null}
              {/* Отображение статусов */}
              {bleStatus && (
                <div style={{
                  marginTop: '15px',
                  padding: '12px',
                  borderRadius: '8px',
                  backgroundColor:
                    bleStatus === 'found' ? '#d4edda' :
                      bleStatus === 'scanning' ? '#fff3cd' :
                        bleStatus === 'not_found' ? '#f8d7da' :
                          '#e2e3e5',
                  border: '1px solid #ddd',
                  textAlign: 'center'
                }}>
                  {bleStatus === 'scanning' && '📡 Opening scanner for UUID... Check your phone!'}
                  {bleStatus === 'found' && `✅ Matched Device Found: ${deviceName}`}
                  {bleStatus === 'not_found' && '⚠️ Device with this UUID not found (or canceled)'}
                  {bleStatus === 'not_supported' && 'ℹ️ Bluetooth API not supported'}
                </div>
              )}
            </div>
          </>
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
