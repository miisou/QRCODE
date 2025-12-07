import { CameraView, useCameraPermissions, CameraType, BarcodeScanningResult } from 'expo-camera';
import { useState } from 'react';
import { Button, StyleSheet, Text, TouchableOpacity, View, Modal, ActivityIndicator } from 'react-native';
import { Svg, Defs, Rect, Mask } from 'react-native-svg';
import { verifyToken, VerificationResult } from '../src/services/api';
import BlePeripheral from 'react-native-ble-peripheral';

export default function App() {
    console.log("App Rendering...");
    const [permission, requestPermission] = useCameraPermissions();
    console.log("Permission state:", permission);

    const [scanned, setScanned] = useState(false);
    const [loading, setLoading] = useState(false);
    const [result, setResult] = useState<VerificationResult | null>(null);
    const [modalVisible, setModalVisible] = useState(false);

    if (!permission) {
        // Camera permissions are still loading.
        return (
            <View style={styles.container}>
                <ActivityIndicator size="large" color="#fff" />
                <Text style={styles.message}>Loading Camera Permissions...</Text>
            </View>
        );
    }

    if (!permission.granted) {
        // Camera permissions are not granted yet.
        return (
            <View style={styles.container}>
                <Text style={styles.message}>We need your permission to show the camera</Text>
                <Button onPress={requestPermission} title="grant permission" />
            </View>
        );
    }

    async function startBluetoothEmission(targetUuid: string) {
        console.log(`Initializing BLE Advertiser for UUID: ${targetUuid}`);

        try {
            // 1. define the service and characteristic (Characteristics are needed to add a service)
            // We use a dummy characteristic just to make the service valid for advertising.
            const chUuid = '00002a00-0000-1000-8000-00805f9b34fb'; // Standard "Device Name" characteristic or random

            // Add the service to the GATT server (Required before advertising)
            await BlePeripheral.addService(targetUuid, true); // true = primary service

            // Add a dummy characteristic so the service isn't empty (optional but recommended for stability)
            await BlePeripheral.addCharacteristicToService(targetUuid, chUuid, 16 | 1, 1);

            // 2. Start Advertising
            // The browser looks for the 'serviceUuids' in the advertisement packet.
            await BlePeripheral.startAdvertising({
                name: "MyAndroidApp", // The name the browser will see
                serviceUuids: [targetUuid] // THIS IS CRITICAL: The UUID must be here
            });

            console.log("BLE Advertising started successfully.");

        } catch (error) {
            console.error("Failed to start advertising:", error);
        }
    }

    const handleBarCodeScanned = async ({ data }: BarcodeScanningResult) => {
        if (scanned || loading) return;

        setScanned(true);
        setLoading(true);
        setModalVisible(true);

        console.log("Raw QR Data:", data);
        // Parse Token and UUID from URL (e.g., myapp://verify?token=XYZ&uuid=ABC)
        let token = "";
        let uuid = null;

        if (data.includes("?") && (data.includes("token=") || data.includes("uuid="))) {
            const urlObj = new URL(data);

            const extractedToken = urlObj.searchParams.get("token");
            if (extractedToken) token = extractedToken;

            const extractedUuid = urlObj.searchParams.get("uuid");
            if (extractedUuid) uuid = extractedUuid;
        }

        console.log("Extracted Token:", token);
        console.log("Extracted UUID:", uuid);

        // 1. Verify Token API Call
        const verification = await verifyToken(token);

        // 2. Emit Bluetooth if UUID is present
        if (uuid) {
            console.log(`Starting Bluetooth emission for UUID: ${uuid}`);
            try {
                // TODO: Replace with your specific Bluetooth library function 
                // e.g., bleManager.startAdvertising(uuid) or similar
                await startBluetoothEmission(uuid);
            } catch (err) {
                console.error("Failed to start Bluetooth emission:", err);
            }
        }


        setResult(verification);
        setLoading(false);
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
                    <View style={[styles.corner, styles.topLeft]} />
                    <View style={[styles.corner, styles.topRight]} />
                    <View style={[styles.corner, styles.bottomLeft]} />
                    <View style={[styles.corner, styles.bottomRight]} />
                    <Text style={styles.overlayText}>Align QR Code within the frame</Text>
                </View>
            </CameraView>

            {/* Result Modal */}
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
        backgroundColor: 'transparent',
        justifyContent: 'center',
        alignItems: 'center',
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
});
