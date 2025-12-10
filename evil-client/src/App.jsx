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
  const [isModalOpen, setIsModalOpen] = useState(false);

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
      setIsModalOpen(true);
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

  const handleOpenModal = () => {
    setIsModalOpen(true);
  };

  const handleCloseModal = () => {
    setIsModalOpen(false);
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
    <div className="gov-portal-page">
      {/* Фоновый макет правительственного портала */}
      <div className="gov-portal-layout">
        <header className="gov-portal-header">
          <div className="gov-skeleton-logo" />
          <div className="gov-skeleton-nav">
            <div className="gov-skeleton-pill" />
            <div className="gov-skeleton-pill" />
            <div className="gov-skeleton-pill" />
            <div className="gov-skeleton-pill" />
          </div>
        </header>

        <div className="gov-portal-breadcrumb" />

        <main className="gov-portal-main">
          <section className="gov-portal-main-content">
            <div className="gov-skeleton-heading" />
            <div className="gov-skeleton-paragraph" />
            <div className="gov-skeleton-paragraph" />
            <div className="gov-skeleton-large-block" />
            <div className="gov-skeleton-paragraph short" />
            <div className="gov-skeleton-paragraph" />
            <div className="gov-skeleton-paragraph" />
          </section>

          <aside className="gov-portal-sidebar">
            <div className="gov-skeleton-card" />
            <div className="gov-skeleton-card" />
            <div className="gov-skeleton-card" />
          </aside>
        </main>
      </div>

      {/* Плавающая кнопка "Verify with mObywatel" в правом нижнем углу */}
      <button className="verify-fab" onClick={handleOpenModal}>
        <img src="/image.png" alt="Polish Eagle" className="verify-fab-icon" />
        <span className="verify-fab-text">Verify with mObywatel</span>
      </button>

      {/* Модальное окно с функционалом верификации */}
      {isModalOpen && (
        <div className="verify-modal-backdrop" onClick={handleCloseModal}>
          <div className="verify-modal" onClick={(e) => e.stopPropagation()}>
            <div className="verify-modal-header">
              <div className="verify-modal-title">
                <img src="/image.png" alt="Polish Eagle" className="verify-modal-icon" />
                <span>Verify with mObywatel</span>
              </div>
              <button className="verify-modal-close" onClick={handleCloseModal} aria-label="Close">
                ×
              </button>
            </div>

            <div className="verify-modal-body">
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

                  <div className="verify-token-box">
                    <p className="verify-token-label">Token (Nonce)</p>
                    <code className="verify-token-code">{session.nonce}</code>
                  </div>

                  <div className="verify-ble-section">
                    {!bleStatus || bleStatus === 'not_found' || bleStatus === 'canceled' ? (
                      <button className="verify-ble-button" onClick={handleManualScan}>
                        <span className="material-symbols-rounded verify-ble-icon">bluetooth</span>
                        <span>Use Bluetooth Verification</span>
                      </button>
                    ) : null}

                    {bleStatus && (
                      <div className={`verify-ble-status verify-ble-status-${bleStatus}`}>
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
                <div
                  className={`verify-result-box ${
                    session.result.verdict === 'TRUSTED'
                      ? 'verify-result-trusted'
                      : 'verify-result-untrusted'
                  }`}
                >
                  <h2 className="verify-result-title">
                    Verification Result: {session.result.verdict}
                  </h2>
                  <p className="verify-result-score">
                    Trust Score: <strong>{session.result.trust_score}/100</strong>
                  </p>
                  {session.result.verdict !== 'TRUSTED' && (
                    <div className="verify-result-issues">
                      <h4>Issues:</h4>
                      <ul>
                        {session.result.logs
                          .filter((log) => !log.includes('PASS'))
                          .map((log, i) => (
                            <li key={i}>{log}</li>
                          ))}
                      </ul>
                    </div>
                  )}
                </div>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

export default App;
