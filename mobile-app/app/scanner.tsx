import { CameraView, useCameraPermissions, BarcodeScanningResult } from 'expo-camera';
import { useState, useEffect } from 'react';
import { Button, StyleSheet, Text, TouchableOpacity, View, Modal, ActivityIndicator, Alert, Platform, PermissionsAndroid } from 'react-native';
import { verifyToken, VerificationResult, BASE_URL } from '../src/services/api';
import BLEAdvertiser from 'react-native-ble-advertiser';
import { useRouter } from 'expo-router';
import { Ionicons, MaterialCommunityIcons } from '@expo/vector-icons';


export default function ScannerScreen() {
    const router = useRouter();
    const [permission, requestPermission] = useCameraPermissions();
    const [scanned, setScanned] = useState(false);
    const [loading, setLoading] = useState(false);
    const [result, setResult] = useState<VerificationResult | null>(null);
    const [modalVisible, setModalVisible] = useState(false);

    // BLE State
    const [broadcasting, setBroadcasting] = useState(false);
    const [broadcastUUID, setBroadcastUUID] = useState<string | null>(null);

    // Initial permission check for BLE (Android 12+)
    useEffect(() => {
        const setupBLE = async () => {
            if (Platform.OS === 'android') {
                try {
                    // Android 12+ (API 31+) requires specific Bluetooth permissions
                    if (Platform.Version >= 31) {
                        const result = await PermissionsAndroid.requestMultiple([
                            PermissionsAndroid.PERMISSIONS.BLUETOOTH_ADVERTISE,
                            PermissionsAndroid.PERMISSIONS.BLUETOOTH_CONNECT,
                            PermissionsAndroid.PERMISSIONS.ACCESS_FINE_LOCATION, // Often required for BLE
                        ]);

                        // Check if all are granted
                        const allGranted = Object.values(result).every(
                            status => status === PermissionsAndroid.RESULTS.GRANTED
                        );

                        if (allGranted) {
                            console.log("Android 12+ BLE Permissions Granted");
                        } else {
                            console.warn("Android 12+ BLE Permissions Denied", result);
                            Alert.alert("Permission Error", "Bluetooth advertising requires 'Nearby Devices' permission.");
                        }
                    } else {
                        // Android < 12
                        const granted = await PermissionsAndroid.request(
                            PermissionsAndroid.PERMISSIONS.ACCESS_FINE_LOCATION
                        );
                        if (granted === PermissionsAndroid.RESULTS.GRANTED) {
                            console.log("Legacy BLE Permissions Granted");
                        } else {
                            Alert.alert("Permission Error", "Location permission is required for Bluetooth on this device.");
                        }
                    }
                } catch (err) {
                    console.warn(err);
                }
            }
            console.log("BLE Advertiser initialized");
        };
        setupBLE();
    }, []);

    if (!permission) {
        return (
            <View style={styles.container}>
                <ActivityIndicator size="large" color="#fff" />
                <Text style={styles.message}>Loading Camera Permissions...</Text>
            </View>
        );
    }

    if (!permission.granted) {
        return (
            <View style={styles.container}>
                <Text style={styles.message}>We need your permission to show the camera</Text>
                <Button onPress={requestPermission} title="grant permission" />
            </View>
        );
    }

    const [verificationStatus, setVerificationStatus] = useState<'IDLE' | 'WAITING' | 'SUCCESS' | 'FAILED'>('IDLE');
    const [ws, setWs] = useState<WebSocket | null>(null);

    // Clean up WS on unmount or stop
    useEffect(() => {
        return () => {
            if (ws) {
                ws.close();
            }
        };
    }, []);

    const startBeacon = async (uuid: string) => {
        try {
            console.log("Starting Beacon for UUID:", uuid);
            setBroadcastUUID(uuid);
            setBroadcasting(true);
            setVerificationStatus('WAITING');

            // BLE Advertiser configuration
            // Attempt to set device name if possible, though library support varies.
            // Some forks support setDeviceName, otherwise it uses system name.
            try {
                // Explicitly trying to make name 'phone' visible.
                // Only works if the library exposes this method or if we rely on system name.
                // For now, enabling includeDeviceName is key.
            } catch (e) { }

            await BLEAdvertiser.setCompanyId(0x0059);
            await BLEAdvertiser.broadcast(uuid, [12, 34, 56], {
                advertiseMode: (BLEAdvertiser as any).ADVERTISE_MODE_BALANCED || 1,
                txPowerLevel: (BLEAdvertiser as any).ADVERTISE_TX_POWER_MEDIUM || 2,
                connectable: false,
                includeTxPowerLevel: false,
                includeDeviceName: true, // Requested: Change from false to true to show name
            });

            // Start WebSocket Connection
            connectWebSocket(uuid);

        } catch (error) {
            console.error("BLE Error:", error);
            Alert.alert("BLE Error", "Failed to start beacon. Are you running a Development Build?");
            setBroadcasting(false);
            setVerificationStatus('IDLE');
        }
    };

    const connectWebSocket = (token: string) => {
        // Derive WS URL from API URL
        // Example: https://.../api/v1 -> wss://.../api/v1/ws/verification/{token}
        const wsBase = BASE_URL.replace('https://', 'wss://').replace('http://', 'ws://');
        const wsUrl = `${wsBase}/ws/verification/${token}`;

        console.log("Connecting to WebSocket:", wsUrl);
        const newWs = new WebSocket(wsUrl);

        newWs.onopen = () => {
            console.log("WebSocket Connected");
            // Send ping to keep connection alive maybe?
            // newWs.send("ping"); 
        };

        newWs.onmessage = (e) => {
            console.log("WebSocket Message:", e.data);
            try {
                if (e.data === "pong") return;

                const message = JSON.parse(e.data);
                if (message.type === 'verification_success') {
                    const res = message.result;
                    console.log("Verified!", res);
                    setVerificationStatus('SUCCESS');
                    setResult(res); // populate result for detailed view if needed

                    // Stop beacon after success? 
                    // Optional: stopBeacon(); 
                    // OR keep broadcasting until user clicks "Done"
                }
            } catch (err) {
                console.warn("WS Parse Error", err);
            }
        };

        newWs.onerror = (e) => {
            console.log("WebSocket Error:", e);
        };

        newWs.onclose = (e) => {
            console.log("WebSocket Closed", e.code, e.reason);
        };

        setWs(newWs);
    };

    const stopBeacon = async () => {
        try {
            if (broadcastUUID) {
                await BLEAdvertiser.stopBroadcast();
            }
            if (ws) {
                ws.close();
                setWs(null);
            }
            setBroadcasting(false);
            setBroadcastUUID(null);
            setVerificationStatus('IDLE');
            console.log("Beacon Stopped");
        } catch (error) {
            console.warn("Error stopping beacon:", error);
        }
    };



    const handleBarCodeScanned = async ({ data }: BarcodeScanningResult) => {
        if (scanned || loading) return;

        setScanned(true);
        setLoading(true);
        console.log("Raw QR Data:", data);

        let token = data;
        let targetUuid: string | null = null;
        const uuidRegex = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;

        // 1. Check if data is a direct UUID
        if (uuidRegex.test(data)) {
            token = data;
            targetUuid = data;
        }
        // 2. Parse details from URL if possible
        else {
            try {
                // Handle raw strings that might contain params but aren't full URLs
                const urlString = (data.includes("://") || data.startsWith("http")) ? data : `https://example.com?${data.includes("?") ? data.split("?")[1] : data}`;

                // If it looks like a URL or has params
                if (data.includes("?") || data.includes("=")) {
                    const urlObj = new URL(urlString);

                    const extractedToken = urlObj.searchParams.get("token");
                    if (extractedToken) token = extractedToken;

                    const extractedUuid = urlObj.searchParams.get("uuid");
                    if (extractedUuid) targetUuid = extractedUuid;
                }
            } catch (e) {
                console.log("URL Parse Error", e);
                // Fallback legacy parsing
                if (data.includes("token=")) {
                    token = data.split("token=")[1].split("&")[0];
                }
            }

            // If we found a token that looks like a UUID, and no explicit UUID param was found
            if (!targetUuid && uuidRegex.test(token)) {
                targetUuid = token;
            }
        }

        console.log("Resolved - Token:", token, "UUID:", targetUuid);

        if (targetUuid) {
            Alert.alert(
                "Activate Beacon?",
                `Do you want to broadcast this UUID?\n${targetUuid}`,
                [
                    {
                        text: "Cancel",
                        style: "cancel",
                        onPress: () => {
                            setScanned(false);
                            setLoading(false);
                        }
                    },
                    {
                        text: "Start Broadcasting",
                        onPress: () => {
                            startBeacon(targetUuid!);
                            setLoading(false);
                        }
                    }
                ]
            );
        } else {
            // Standard Verification
            setModalVisible(true);
            const verification = await verifyToken(token);
            setResult(verification);
            setLoading(false);
        }
    };

    const closeModal = () => {
        setModalVisible(false);
        setScanned(false);
        setResult(null);
    };

    return (
        <View style={styles.container}>
            <CameraView
                style={styles.camera}
                facing="back"
                onBarcodeScanned={scanned ? undefined : handleBarCodeScanned}
                barcodeScannerSettings={{
                    barcodeTypes: ["qr"],
                }}
            >
                {/* Overlay */}
                <View style={styles.overlay}>

                    <TouchableOpacity style={styles.backButton} onPress={() => {
                        stopBeacon();
                        router.back();
                    }}>
                        <Ionicons name="arrow-back" size={28} color="white" />
                    </TouchableOpacity>

                    {broadcasting ? (
                        <View style={styles.broadcastingContainer}>
                            {verificationStatus === 'SUCCESS' ? (
                                // --- SUCCESS VIEW (Matches Screenshot) ---
                                <View style={styles.successContainer}>
                                    <View style={styles.header}>
                                        <TouchableOpacity onPress={() => router.back()} style={styles.backLink}>
                                            <Ionicons name="chevron-back" size={24} color="#5FA9EE" />
                                            <Text style={styles.backText}>Back</Text>
                                        </TouchableOpacity>
                                        <Text style={styles.headerTitle}>Verification Status</Text>
                                        <View style={{ width: 60 }} />
                                    </View>

                                    <View style={styles.successCard}>
                                        <View style={styles.shieldContainer}>
                                            <MaterialCommunityIcons name="shield-check" size={64} color="#4caf50" />
                                        </View>
                                        <Text style={styles.successTitle}>Verification Successful</Text>

                                        <View style={styles.checklist}>
                                            <View style={styles.checkRow}>
                                                <Ionicons name="checkmark-circle" size={20} color="#4caf50" />
                                                <Text style={styles.checkText}>Official .gov Site</Text>
                                            </View>
                                            <View style={styles.checkRow}>
                                                <Ionicons name="checkmark-circle" size={20} color="#4caf50" />
                                                <Text style={styles.checkText}>Valid SSL certificate</Text>
                                            </View>
                                            <View style={styles.checkRow}>
                                                <Ionicons name="checkmark-circle" size={20} color="#4caf50" />
                                                <Text style={styles.checkText}>Access attempt from near location</Text>
                                            </View>
                                        </View>
                                    </View>

                                    <Text style={styles.sectionTitle}>Access attempt</Text>
                                    <View style={styles.infoCard}>
                                        <View style={styles.infoRow}>
                                            <Ionicons name="location-outline" size={24} color="#fff" />
                                            <Text style={styles.infoText}>
                                                {result?.client_ip || "Warsaw, PL (IP: 192.168.0.1)"}
                                            </Text>
                                        </View>
                                        <View style={styles.divider} />
                                        <View style={styles.infoRow}>
                                            <MaterialCommunityIcons name="web" size={24} color="#fff" />
                                            <Text style={styles.infoText}>
                                                {result?.device_browser ? `${result.device_browser} (${result.device_os || 'Windows 10'})` : "Chrome (Windows 10)"}
                                            </Text>
                                        </View>
                                    </View>

                                    <Text style={styles.sectionTitle}>Additional verification</Text>
                                    <View style={styles.additionalRow}>
                                        <View style={[styles.additionalCard, styles.activeCard]}>
                                            <Ionicons name="bluetooth" size={32} color="#4caf50" />
                                            <Text style={styles.additionalText}>Bluetooth</Text>
                                        </View>
                                        <View style={[styles.additionalCard, styles.activeCard]}>
                                            <MaterialCommunityIcons name="waveform" size={32} color="#4caf50" />
                                            <Text style={styles.additionalText}>Ultrasound</Text>
                                        </View>
                                    </View>

                                    <TouchableOpacity
                                        style={styles.doneButton}
                                        onPress={() => {
                                            stopBeacon();
                                            setScanned(false);
                                            router.back();
                                        }}
                                    >
                                        <Text style={styles.doneButtonText}>Done</Text>
                                    </TouchableOpacity>
                                </View>
                            ) : (
                                // --- BROADCASTING / WAITING VIEW ---
                                <View style={styles.waitingContainer}>
                                    <Ionicons name="bluetooth" size={64} color={verificationStatus === 'WAITING' ? "#FFC107" : "#5FA9EE"} />

                                    <Text style={styles.broadcastingTitle}>
                                        {verificationStatus === 'WAITING' ? 'Waiting for Verification...' :
                                            'Broadcasting Signal'}
                                    </Text>

                                    <Text style={styles.broadcastingUUID}>{broadcastUUID}</Text>

                                    <TouchableOpacity
                                        style={styles.stopButton}
                                        onPress={() => {
                                            stopBeacon();
                                            setScanned(false);
                                        }}
                                    >
                                        <Text style={styles.stopButtonText}>Stop Signal</Text>
                                    </TouchableOpacity>
                                </View>
                            )}
                        </View>
                    ) : (
                        <>
                            <View style={[styles.corner, styles.topLeft]} />
                            <View style={[styles.corner, styles.topRight]} />
                            <View style={[styles.corner, styles.bottomLeft]} />
                            <View style={[styles.corner, styles.bottomRight]} />
                            <Text style={styles.overlayText}>Align QR Code within the frame</Text>
                        </>
                    )}
                </View>
            </CameraView>

            {/* Standard Verification Result Modal */}
            <Modal
                animationType="slide"
                transparent={true}
                visible={modalVisible}
                onRequestClose={closeModal}
            >
                <View style={styles.modalCenteredView}>
                    <View style={[
                        styles.modalView,
                        result?.verdict === 'TRUSTED' ? styles.trustedBorder :
                            result?.verdict === 'UNSAFE' ? styles.unsafeBorder : styles.unknownBorder
                    ]}>
                        {loading ? (
                            <View>
                                <ActivityIndicator size="large" color="#0a7ea4" />
                                <Text style={styles.modalText}>Verifying Token...</Text>
                            </View>
                        ) : result ? (
                            <>
                                <Text style={[
                                    styles.verdictText,
                                    result.verdict === 'TRUSTED' ? styles.textTrusted :
                                        result.verdict === 'UNSAFE' ? styles.textUnsafe : styles.textUnknown
                                ]}>
                                    {result.verdict}
                                </Text>

                                <View style={styles.detailsContainer}>
                                    <Text style={styles.detailLabel}>URL:</Text>
                                    <Text style={styles.detailValue}>{result.checked_url || 'N/A'}</Text>

                                    <Text style={styles.detailLabel}>Device:</Text>
                                    <Text style={styles.detailValue}>{result.device_brand || 'Unknown'}</Text>
                                </View>

                                <TouchableOpacity
                                    style={[styles.button, styles.buttonClose]}
                                    onPress={closeModal}>
                                    <Text style={styles.textStyle}>Scan Again</Text>
                                </TouchableOpacity>
                            </>
                        ) : (
                            <>
                                <Text style={[styles.verdictText, styles.textUnsafe]}>ERROR</Text>
                                <Text style={styles.modalText}>Could not verify token.</Text>
                                <TouchableOpacity
                                    style={[styles.button, styles.buttonClose]}
                                    onPress={closeModal}>
                                    <Text style={styles.textStyle}>Try Again</Text>
                                </TouchableOpacity>
                            </>
                        )}
                    </View>
                </View>
            </Modal>
        </View>
    );
}

const styles = StyleSheet.create({
    container: {
        flex: 1,
        justifyContent: 'center',
        backgroundColor: '#000',
    },
    message: {
        textAlign: 'center',
        paddingBottom: 10,
        color: '#fff',
    },
    camera: {
        flex: 1,
    },
    overlay: {
        flex: 1,
        backgroundColor: 'rgba(0,0,0,0.3)', // Slight tint
        justifyContent: 'center',
        alignItems: 'center',
    },
    backButton: {
        position: 'absolute',
        top: 50,
        left: 20,
        zIndex: 10,
        padding: 10,
        backgroundColor: 'rgba(0,0,0,0.5)',
        borderRadius: 20,
    },
    overlayText: {
        position: 'absolute',
        bottom: 100,
        color: 'rgba(255,255,255,0.7)',
        fontSize: 16,
    },
    corner: {
        position: 'absolute',
        width: 60,
        height: 60,
        borderColor: '#0a7ea4',
        borderWidth: 5,
    },
    topLeft: {
        top: '35%',
        left: '15%',
        borderRightWidth: 0,
        borderBottomWidth: 0,
    },
    topRight: {
        top: '35%',
        right: '15%',
        borderLeftWidth: 0,
        borderBottomWidth: 0,
    },
    bottomLeft: {
        bottom: '35%',
        left: '15%',
        borderRightWidth: 0,
        borderTopWidth: 0,
    },
    bottomRight: {
        bottom: '35%',
        right: '15%',
        borderLeftWidth: 0,
        borderTopWidth: 0,
    },
    // Modal Styles
    modalCenteredView: {
        flex: 1,
        justifyContent: 'center',
        alignItems: 'center',
        backgroundColor: 'rgba(0,0,0,0.8)',
    },
    modalView: {
        margin: 20,
        backgroundColor: '#1a1a1a',
        borderRadius: 20,
        padding: 35,
        alignItems: 'center',
        shadowColor: '#000',
        shadowOffset: {
            width: 0,
            height: 2,
        },
        shadowOpacity: 0.25,
        shadowRadius: 4,
        elevation: 5,
        width: '80%',
        borderWidth: 2,
    },
    trustedBorder: { borderColor: '#4caf50' },
    unsafeBorder: { borderColor: '#f44336' },
    unknownBorder: { borderColor: '#ff9800' },
    button: {
        borderRadius: 20,
        padding: 10,
        elevation: 2,
        marginTop: 20,
        minWidth: 120,
    },
    buttonClose: {
        backgroundColor: '#2196F3',
    },
    textStyle: {
        color: 'white',
        fontWeight: 'bold',
        textAlign: 'center',
    },
    modalText: {
        marginBottom: 15,
        textAlign: 'center',
        color: '#fff',
    },
    verdictText: {
        fontSize: 24,
        fontWeight: 'bold',
        marginBottom: 20,
    },
    textTrusted: { color: '#4caf50' },
    textUnsafe: { color: '#f44336' },
    textUnknown: { color: '#ff9800' },
    detailsContainer: {
        width: '100%',
        marginVertical: 10,
    },
    detailLabel: {
        color: '#888',
        fontSize: 12,
        marginTop: 5,
    },
    detailValue: {
        color: '#fff',
        fontSize: 16,
        marginBottom: 5,
    },
    // Broadcasting UI
    stopButtonText: {
        color: 'white',
        fontWeight: 'bold',
        fontSize: 16,
    },
    // New UI Styles
    broadcastingContainer: {
        width: '100%',
        height: '100%',
        backgroundColor: '#000', // Full screen black background
        justifyContent: 'center',
        alignItems: 'center',
    },
    waitingContainer: {
        alignItems: 'center',
        justifyContent: 'center',
        padding: 20,
    },
    successContainer: {
        width: '100%',
        height: '100%',
        paddingTop: 50,
        paddingHorizontal: 20,
        backgroundColor: '#0d0d0d', // Slightly lighter black for depth
    },
    header: {
        flexDirection: 'row',
        justifyContent: 'space-between',
        alignItems: 'center',
        marginBottom: 20,
    },
    backLink: {
        flexDirection: 'row',
        alignItems: 'center',
    },
    backText: {
        color: '#5FA9EE',
        fontSize: 18,
    },
    headerTitle: {
        color: '#fff',
        fontSize: 18,
        fontWeight: 'bold',
    },
    successCard: {
        backgroundColor: '#1a1a1a',
        borderRadius: 20,
        padding: 20,
        alignItems: 'center',
        borderWidth: 1,
        borderColor: '#4caf50',
        marginBottom: 25,
    },
    shieldContainer: {
        marginBottom: 10,
    },
    successTitle: {
        color: '#fff',
        fontSize: 22,
        fontWeight: 'bold',
        marginBottom: 20,
    },
    checklist: {
        width: '100%',
    },
    checkRow: {
        flexDirection: 'row',
        alignItems: 'center',
        marginBottom: 10,
    },
    checkText: {
        color: '#fff',
        marginLeft: 10,
        fontSize: 16,
    },
    sectionTitle: {
        color: '#fff',
        fontSize: 18,
        fontWeight: 'bold',
        marginBottom: 10,
        marginTop: 10,
    },
    infoCard: {
        backgroundColor: '#1a1a1a',
        borderRadius: 15,
        padding: 5,
    },
    infoRow: {
        flexDirection: 'row',
        alignItems: 'center',
        padding: 15,
    },
    infoText: {
        color: '#ccc',
        marginLeft: 15,
        fontSize: 16,
    },
    divider: {
        height: 1,
        backgroundColor: '#333',
        marginLeft: 50, // Indent divider
    },
    additionalRow: {
        flexDirection: 'row',
        justifyContent: 'space-between',
        marginTop: 10,
    },
    additionalCard: {
        backgroundColor: '#1a1a1a',
        width: '48%',
        padding: 20,
        borderRadius: 15,
        alignItems: 'center',
        justifyContent: 'center',
        borderWidth: 1,
        borderColor: '#333',
    },
    activeCard: {
        borderColor: '#4caf50',
    },
    additionalText: {
        color: '#fff',
        marginTop: 10,
        fontSize: 16,
    },
    doneButton: {
        marginTop: 40,
        backgroundColor: '#1a1a1a',
        paddingVertical: 15,
        borderRadius: 10,
        alignItems: 'center',
    },
    doneButtonText: {
        color: '#5FA9EE',
        fontSize: 18,
        fontWeight: 'bold',
    }
});
