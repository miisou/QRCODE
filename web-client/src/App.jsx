import React, { useState, useEffect } from 'react';
import VerificationForm from './components/VerificationForm';
import QRCodeDisplay from './components/QRCodeDisplay';
import api, { initSession, pollSession } from './services/api';
import { generateBLEUUID, scanForDevice, checkProximity } from './services/bluetoothScanner';
import './App.css';


function App() {
  const [session, setSession] = useState(null);
  const [loading, setLoading] = useState(false);
  const [bleStatus, setBleStatus] = useState(null); // 'scanning', 'found', 'not_found', 'error'
  const [bleUUID, setBleUUID] = useState(null);

  const handleGenerate = async () => {
    setLoading(true);
    setExpirationMessage(null);
    setBleStatus(null);

    // Generate BLE UUID for this session
    const newBleUUID = generateBLEUUID();
    setBleUUID(newBleUUID);

    try {
      const data = await initSession();
      // Update QR payload to include BLE UUID
      const updatedData = {
        ...data,
        qr_payload: `${data.qr_payload}&ble=${newBleUUID}`
      };
      setSession(updatedData);


      setTimeout(() => scanForDevice(newBleUUID), 1000);
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
    setBleStatus(null);
    setBleUUID(null);
  };

  const scanForDevice = async (targetUUID) => {
    try {
      console.log(`Запрашиваем устройство с сервисом: ${targetUUID}`);

      // 1. Вызов окна выбора устройства
      // Важно: Браузер покажет ТОЛЬКО те устройства, которые рекламируют этот UUID.
      // Если телефон не начал рекламу - список будет пуст.
      const device = await navigator.bluetooth.requestDevice({
        filters: [
          { services: [targetUUID] }
        ]
      });

      console.log(`Пользователь выбрал устройство: ${device.name}`);

      // 2. Проверка соединения (Proof of Proximity)
      // Просто выбора недостаточно (вдруг устройство выключилось секунду назад).
      // Нужно установить GATT соединение.
      if (device.gatt) {
        const server = await device.gatt.connect();

        console.log("Успешное подключение к GATT серверу!");

        // Здесь можно прочитать характеристику, если нужно передать данные,
        // но для проверки близости факта connect() достаточно.

        // 3. Отключаемся и возвращаем успех
        setTimeout(() => device.gatt.disconnect(), 1000);

        return {
          supported: true,
          found: true,
          rssi: -50, // Фейковый RSSI, т.к. при прямом подключении мы его не знаем, но связь есть
          device: device
        };
      } else {
        throw new Error("GATT сервер недоступен");
      }

    } catch (error) {
      // Обработка ошибок
      if (error.name === 'NotFoundError') {
        console.log('Пользователь закрыл окно выбора или не выбрал устройство.');
        // Это не "ошибка технологии", это отмена действия пользователем
        return { supported: true, found: false };
      }

      console.error("Ошибка Bluetooth:", error);
      return { supported: true, found: false, error: error.message };
    }
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
        <h1>GovVerify</h1>
      </header>
      <main>
        {!session ? (
          <VerificationForm
            onGenerate={handleGenerate}
            expirationMessage={expirationMessage}
          />
        ) : (
          <>
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
            <div style={{
              marginTop: '20px',
              padding: '15px',
              backgroundColor: '#f5f5f5',
              borderRadius: '8px',
              textAlign: 'center'
            }}>
              <p style={{ margin: '0 0 10px 0', fontWeight: 'bold' }}>Token (Nonce):</p>
              <div style={{
                display: 'flex',
                gap: '10px',
                alignItems: 'center',
                justifyContent: 'center'
              }}>
                <code style={{
                  padding: '8px 12px',
                  backgroundColor: '#fff',
                  border: '1px solid #ddd',
                  borderRadius: '4px',
                  fontSize: '14px',
                  fontFamily: 'monospace',
                  wordBreak: 'break-all'
                }}>
                  {session.nonce}
                </code>
                <button
                  onClick={() => {
                    navigator.clipboard.writeText(session.nonce);
                    alert('Token copied to clipboard!');
                  }}
                  style={{
                    padding: '8px 16px',
                    backgroundColor: '#007bff',
                    color: 'white',
                    border: 'none',
                    borderRadius: '4px',
                    cursor: 'pointer',
                    fontSize: '14px'
                  }}
                >
                  Copy
                </button>
              </div>
            </div>

            {/* BLE Proximity Status */}
            {bleStatus && (
              <div style={{
                marginTop: '20px',
                padding: '12px',
                borderRadius: '8px',
                backgroundColor:
                  bleStatus === 'found' ? '#d4edda' :
                    bleStatus === 'scanning' ? '#fff3cd' :
                      bleStatus === 'not_supported' ? '#d1ecf1' :
                        '#f8d7da',
                border: '1px solid ' + (
                  bleStatus === 'found' ? '#c3e6cb' :
                    bleStatus === 'scanning' ? '#ffeaa7' :
                      bleStatus === 'not_supported' ? '#bee5eb' :
                        '#f5c6cb'
                ),
                textAlign: 'center'
              }}>
                <small>
                  {bleStatus === 'scanning' && '📡 Scanning for phone nearby...'}
                  {bleStatus === 'found' && '✅ Phone detected nearby (BLE proximity confirmed)'}
                  {bleStatus === 'not_found' && '⚠️ Phone not detected via BLE'}
                  {bleStatus === 'far' && '⚠️ Phone detected but too far'}
                  {bleStatus === 'not_supported' && 'ℹ️ BLE not supported (proximity check skipped)'}
                  {bleStatus === 'error' && '❌ BLE scanning error (proximity check skipped)'}
                </small>
              </div>
            )}
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
