import axios from 'axios';

const api = axios.create({
    baseURL: 'http://localhost:8000/api/v1',
    headers: {
        'Content-Type': 'application/json',
    },
});

export const initSession = async (url) => {
    const response = await api.post('/session/init', { url });
    return response.data;
};

export const verifySession = async (token) => {
    // This endpoint is primarily for Mobile Client, but used here for testing or status check?
    // Actually, Web Client doesn't verify. It just initiates.
    // The Mobile Client verifies.
    // But maybe we want to poll status? The MVP plan didn't specify polling.
    // The MVP plan says "WC stops network activity".
    // So we don't need verify here.
    return;
};

export default api;
