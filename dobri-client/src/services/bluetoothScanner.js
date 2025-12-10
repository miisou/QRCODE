// services/bluetoothScanner.js

// Вспомогательная функция для генерации UUID (вернули её, так как она нужна)
export function generateBLEUUID() {
    return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, function (c) {
        const r = Math.random() * 16 | 0, v = c === 'x' ? r : (r & 0x3 | 0x8);
        return v.toString(16);
    });
}

// Запрос устройства с конкретным UUID сервиса
export function requestDeviceWithUUID(uuid) {
    const result = {
        supported: false,
        found: false,
        name: null,
        error: null
    };

    if (!('bluetooth' in navigator)) {
        result.error = 'Bluetooth not supported in this browser';
        return Promise.resolve(result);
    }

    result.supported = true;
    const normalizedUUID = uuid.toLowerCase();

    // Запрашиваем устройство, которое рекламирует именно этот сервис
    return navigator.bluetooth.requestDevice({
        filters: [{ services: [normalizedUUID] }],
        // optionalServices нужен, если вы планируете потом подключаться и читать данные
        optionalServices: [normalizedUUID]
    })
        .then(device => {
            result.found = true;
            result.name = device.name;
            return result;
        })
        .catch(error => {
            // Ошибка возникает, если устройств не найдено или пользователь нажал "Отмена"
            console.error("Bluetooth Scan Error:", error);
            result.error = error.message;
            return result;
        });
}