// Bluetooth Low Energy Scanner for Proximity Verification
// Scans for BLE devices advertising a specific UUID

export function generateBLEUUID() {
    // Generate RFC4122 v4 UUID
    return ([1e7] + -1e3 + -4e3 + -8e3 + -1e11).replace(/[018]/g, c =>
        (c ^ crypto.getRandomValues(new Uint8Array(1))[0] & 15 >> c / 4).toString(16)
    );
}

function normalizeUUID(uuid) {
    return (uuid || '').trim().toLowerCase();
}

export async function scanForDevice(uuid, timeoutMs = 30000) {
    const result = {
        supported: false,
        found: false,
        rssi: null,
        error: null
    };

    // Check if Bluetooth API is available
    if (!('bluetooth' in navigator)) {
        result.error = 'Bluetooth not supported in this browser';
        return result;
    }

    const lowercaseUUID = normalizeUUID(uuid);

    // Try requestLEScan first (experimental, requires flag)
    if ('requestLEScan' in navigator.bluetooth) {
        try {
            result.supported = true;
            const controller = new AbortController();
            let scanTimeout;

            const deviceFound = await new Promise((resolve) => {
                scanTimeout = setTimeout(() => {
                    controller.abort();
                    resolve(false);
                }, timeoutMs);

                navigator.bluetooth.requestLEScan({
                    acceptAllAdvertisements: true,
                    keepRepeatedDevices: false
                }).then((scan) => {
                    const onAdvertisement = (event) => {
                        const uuids = (event.serviceUuids || []).map(u => normalizeUUID(u));
                        if (uuids.includes(lowercaseUUID)) {
                            result.rssi = event.rssi || null;
                            clearTimeout(scanTimeout);
                            navigator.bluetooth.removeEventListener('advertisementreceived', onAdvertisement);
                            controller.abort();
                            scan.stop();
                            resolve(true);
                        }
                    };

                    navigator.bluetooth.addEventListener('advertisementreceived', onAdvertisement, {
                        signal: controller.signal
                    });
                }).catch((e) => {
                    clearTimeout(scanTimeout);
                    result.error = e.message;
                    resolve(false);
                });
            });

            result.found = deviceFound;
            return result;

        } catch (e) {
            result.error = e.message;
            return result;
        }
    }

    // Fallback: requestDevice (shows chooser UI)
    if ('requestDevice' in navigator.bluetooth) {
        try {
            result.supported = true;
            const device = await Promise.race([
                navigator.bluetooth.requestDevice({
                    filters: [{ services: [uuid] }],
                    optionalServices: [uuid]
                }),
                new Promise((_, reject) =>
                    setTimeout(() => reject(new Error('Timeout')), timeoutMs)
                )
            ]);

            result.found = !!device;
            return result;

        } catch (e) {
            // User canceled or timeout
            result.error = e.message;
            return result;
        }
    }

    result.error = 'No Bluetooth scan method available';
    return result;
}

export function checkProximity(rssi) {
    // RSSI (Received Signal Strength Indicator)
    // Typically ranges from -100 (far) to 0 (very close)
    // > -60 dBm indicates close proximity (within ~2 meters)
    if (rssi === null) return false;
    return rssi > -60;
}
