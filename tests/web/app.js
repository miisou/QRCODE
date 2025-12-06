/* global navigator */
const $ = (sel) => document.querySelector(sel);
const uuidEl = $('#uuid');
const btnGenerate = $('#btn-generate');
const btnCopy = $('#btn-copy');
const genStatus = $('#gen-status');
const btnScan = $('#btn-scan');
const scanTimer = $('#scan-timer');
const resultEl = $('#result');

let currentUUID = '';

function generateUUID() {
  // RFC4122 v4
  // eslint-disable-next-line no-bitwise
  return ([1e7]+-1e3+-4e3+-8e3+-1e11).replace(/[018]/g, (c) =>
    (c ^ crypto.getRandomValues(new Uint8Array(1))[0] & 15 >> c / 4).toString(16)
  );
}

btnGenerate.addEventListener('click', () => {
  currentUUID = generateUUID();
  uuidEl.value = currentUUID;
  btnCopy.disabled = false;
  genStatus.textContent = 'UUID сгенерирован';
  resultEl.textContent = 'Ожидание запуска сканирования...';
  resultEl.className = 'muted';
});

btnCopy.addEventListener('click', async () => {
  if (!currentUUID) return;
  try {
    await navigator.clipboard.writeText(currentUUID);
    genStatus.textContent = 'Скопировано в буфер обмена';
  } catch {
    genStatus.textContent = 'Не удалось скопировать';
  }
});

function setResult(text, ok = null) {
  resultEl.textContent = text;
  resultEl.className = ok === null ? 'muted' : ok ? 'ok' : 'err';
}

function normalizeUUID(u) {
  return (u || '').trim().toLowerCase();
}

async function scanWithRequestLEScan(uuid, ms) {
  if (!('bluetooth' in navigator) || !('requestLEScan' in navigator.bluetooth)) {
    return { supported: false };
  }
  try {
    // Browsers vary: some require chrome://flags/#enable-experimental-web-platform-features
    const controller = new AbortController();
    const found = { ok: false };
    const timer = setTimeout(() => {
      controller.abort();
    }, ms);

    const lowercaseTarget = normalizeUUID(uuid);
    const scan = await navigator.bluetooth.requestLEScan({
      // Some implementations require acceptAllAdvertisements to see service UUIDs
      acceptAllAdvertisements: true,
      keepRepeatedDevices: false,
      // Optionally you can try filters: [{ services: [uuid] }]
    });

    const onAdv = (event) => {
      const uuids = (event.serviceUuids || []).map((x) => normalizeUUID(x));
      if (uuids.includes(lowercaseTarget)) {
        found.ok = true;
        clearTimeout(timer);
        navigator.bluetooth.removeEventListener('advertisementreceived', onAdv);
        controller.abort();
      }
    };
    navigator.bluetooth.addEventListener('advertisementreceived', onAdv, { signal: controller.signal });

    await new Promise((resolve) => {
      controller.signal.addEventListener('abort', resolve, { once: true });
    });

    try { scan.stop(); } catch (_) { /* noop */ }
    return { supported: true, found: found.ok };
  } catch (e) {
    return { supported: true, error: String(e) };
  }
}

async function scanWithRequestDevice(uuid, ms) {
  if (!('bluetooth' in navigator) || !('requestDevice' in navigator.bluetooth)) {
    return { supported: false };
  }
  // requestDevice requires a user gesture and shows chooser; we treat "device selected" as FOUND
  // If nothing matches, диалог покажет пустой список; пользователь может отменить.
  const controller = new AbortController();
  const timer = setTimeout(() => {
    // We can't programmatically cancel chooser; user must cancel if timeout exceeded.
    // We only update UI timer; this function resolves on user action.
    // Intentionally no-op here.
  }, ms);
  try {
    const device = await navigator.bluetooth.requestDevice({
      filters: [{ services: [uuid] }],
      optionalServices: [uuid],
    });
    clearTimeout(timer);
    return { supported: true, found: !!device };
  } catch (e) {
    clearTimeout(timer);
    // If user canceled or no devices matched, consider not found within window
    return { supported: true, found: false, error: String(e) };
  }
}

btnScan.addEventListener('click', async () => {
  const uuid = normalizeUUID(uuidEl.value || currentUUID);
  if (!uuid) {
    setResult('Сначала сгенерируйте UUID', false);
    return;
  }

  setResult('Сканирование...', null);
  const totalMs = 30_000;
  const started = Date.now();

  const timerId = setInterval(() => {
    const elapsed = Date.now() - started;
    const remain = Math.max(0, totalMs - elapsed);
    scanTimer.textContent = `Осталось: ${(remain / 1000).toFixed(0)} сек`;
    if (remain <= 0) {
      clearInterval(timerId);
    }
  }, 200);

  // Prefer requestLEScan if available
  const le = await scanWithRequestLEScan(uuid, totalMs);
  if (le.supported) {
    clearInterval(timerId);
    if (le.found) {
      setResult('Найдено в эфире — ОК', true);
    } else {
      setResult(le.error ? `Ошибка сканирования: ${le.error}` : 'Не найдено — ОШИБКА', false);
    }
    scanTimer.textContent = '';
    return;
  }

  // Fallback: requestDevice chooser
  const rd = await scanWithRequestDevice(uuid, totalMs);
  clearInterval(timerId);
  if (rd.supported && rd.found) {
    setResult('Устройство с сервисом найдено (через диалог) — ОК', true);
  } else {
    setResult('Не найдено — ОШИБКА', false);
  }
  scanTimer.textContent = '';
});


