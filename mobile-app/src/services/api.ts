import { Platform } from 'react-native';

// Use 10.0.2.2 for Android Emulator, localhost/IP for physical device
// You can change this to your machine's IP, e.g., 'http://192.168.1.5:8000/api/v1'
// For USB Debugging with Expo Go, we use localhost.
// YOU MUST RUN: adb reverse tcp:8000 tcp:8000
const BASE_URL = 'http://localhost:8000/api/v1';

export interface VerificationResult {
    verdict: 'TRUSTED' | 'UNSAFE' | 'UNKNOWN';
    checked_url?: string;
    device_brand?: string;
    device_os?: string;
    device_browser?: string;
    is_mobile?: boolean;
    client_ip?: string;
    user_agent?: string;
}

export const verifyToken = async (token: string): Promise<VerificationResult | null> => {
    try {
        console.log(`Verifying token: ${token} at ${BASE_URL}/session/verify`);
        const response = await fetch(`${BASE_URL}/session/verify`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ token }),
        });

        if (response.status === 200) {
            const data = await response.json();
            return data as VerificationResult;
        } else {
            console.warn('Verification failed with status:', response.status);
            return null;
        }
    } catch (error) {
        console.error('API Error:', error);
        return null;
    }
};
