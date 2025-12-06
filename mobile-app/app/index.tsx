import { View, Text, StyleSheet, TouchableOpacity, Image, ScrollView, SafeAreaView, StatusBar } from 'react-native';
import { useRouter } from 'expo-router';
import { Ionicons } from '@expo/vector-icons';
import { BlurView } from 'expo-blur'; // Note: Might need install, otherwise fallback to View

export default function MenuScreen() {
    const router = useRouter();

    const MenuButton = ({ icon, title, subtitle, onPress, isActive = false }) => (
        <TouchableOpacity
            style={[styles.card, isActive && styles.cardActive]}
            onPress={onPress}
            activeOpacity={0.7}
        >
            <View style={styles.iconContainer}>
                <Ionicons name={icon} size={28} color="#fff" />
            </View>
            <View style={styles.textContainer}>
                <Text style={styles.cardTitle}>{title}</Text>
                <Text style={styles.cardSubtitle}>{subtitle}</Text>
            </View>
            <Ionicons name="chevron-forward" size={24} color="#666" />
        </TouchableOpacity>
    );

    return (
        <SafeAreaView style={styles.container}>
            <StatusBar barStyle="light-content" />
            <ScrollView contentContainerStyle={styles.scrollContent}>

                {/* Header */}
                <View style={styles.header}>
                    <View style={styles.logoContainer}>
                        <Image
                            source={require('../assets/images/icon.png')} // Fallback to app icon, user didn't provide logo asset
                            style={styles.logo}
                        />
                    </View>
                    <Text style={styles.title}>QR code</Text>
                </View>

                <Text style={styles.description}>
                    This function allows you to log in to online services and confirm digital documents, both yours and those of another person.
                </Text>

                {/* Buttons List */}
                <View style={styles.listContainer}>

                    {/* Mock Button 1 */}
                    <MenuButton
                        icon="scan-outline"
                        title="Scan the QR code"
                        subtitle="Log in to the website or confirm your digital document."
                        onPress={() => { }}
                    />

                    {/* Mock Button 2 */}
                    <MenuButton
                        icon="qr-code-outline"
                        title="Show the QR code"
                        subtitle="Check the other person's digital document."
                        onPress={() => { }}
                    />

                    {/* Mock Button 3 */}
                    <MenuButton
                        icon="document-text-outline"
                        title="Scan the QR code for the qualified signature"
                        subtitle="Select, if you want to use the code from the signature provider's website."
                        onPress={() => { }}
                    />

                    {/* Real Scanner Button */}
                    <MenuButton
                        icon="shield-checkmark"
                        title="GovVerify Scanner"
                        subtitle="Verify government websites."
                        onPress={() => router.push('/scanner')}
                        isActive={true}
                    />

                </View>
            </ScrollView>

            {/* Mock Tab Bar */}
            <View style={styles.tabBar}>
                <View style={styles.tabItem}>
                    <Ionicons name="folder-outline" size={24} color="#666" />
                    <Text style={styles.tabLabel}>Documents</Text>
                </View>
                <View style={styles.tabItem}>
                    <Ionicons name="grid-outline" size={24} color="#666" />
                    <Text style={styles.tabLabel}>Services</Text>
                </View>
                <View style={styles.tabItem}>
                    <View style={styles.activeTabIcon}>
                        <Ionicons name="qr-code" size={24} color="#5FA9EE" />
                    </View>
                    <Text style={[styles.tabLabel, styles.activeTabLabel]}>QR code</Text>
                </View>
                <View style={styles.tabItem}>
                    <Ionicons name="grid" size={24} color="#666" />
                    <Text style={styles.tabLabel}>More</Text>
                </View>
            </View>
        </SafeAreaView>
    );
}

const styles = StyleSheet.create({
    container: {
        flex: 1,
        backgroundColor: '#0D1117', // Very dark background
    },
    scrollContent: {
        padding: 20,
        paddingBottom: 100, // Space for tab bar
    },
    header: {
        marginTop: 20,
        marginBottom: 20,
    },
    logoContainer: {
        width: 40,
        height: 40,
        backgroundColor: '#D32F2F', // Red bg for logo mock
        borderRadius: 8,
        justifyContent: 'center',
        alignItems: 'center',
        marginBottom: 15,
    },
    logo: {
        width: 30,
        height: 30,
        resizeMode: 'contain',
        tintColor: '#fff',
    },
    title: {
        fontSize: 32,
        fontWeight: 'bold',
        color: '#fff',
    },
    description: {
        fontSize: 16,
        color: '#aaa',
        lineHeight: 24,
        marginBottom: 30,
    },
    listContainer: {
        gap: 16,
    },
    card: {
        flexDirection: 'row',
        alignItems: 'center',
        backgroundColor: '#1C1C1E',
        borderRadius: 16,
        padding: 20,
    },
    cardActive: {
        backgroundColor: '#161B22', // Slightly different for active or just keep same
        borderWidth: 1,
        borderColor: '#5FA9EE',
    },
    iconContainer: {
        marginRight: 16,
    },
    textContainer: {
        flex: 1,
        marginRight: 10,
    },
    cardTitle: {
        fontSize: 16,
        fontWeight: '600',
        color: '#fff',
        marginBottom: 4,
    },
    cardSubtitle: {
        fontSize: 13,
        color: '#888',
        lineHeight: 18,
    },
    // Tab Bar
    tabBar: {
        position: 'absolute',
        bottom: 0,
        left: 0,
        right: 0,
        height: 85,
        backgroundColor: '#0D1117',
        flexDirection: 'row',
        justifyContent: 'space-around',
        alignItems: 'flex-start',
        paddingTop: 15,
        borderTopWidth: 1,
        borderTopColor: '#222',
    },
    tabItem: {
        alignItems: 'center',
        justifyContent: 'center',
    },
    activeTabIcon: {
        marginBottom: 0,
    },
    tabLabel: {
        fontSize: 10,
        color: '#666',
        marginTop: 5,
    },
    activeTabLabel: {
        color: '#5FA9EE',
    },
});
