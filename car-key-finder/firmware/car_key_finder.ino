/*
 * Car Key Finder — ESP32 + CC1101
 *
 * Sends a 125 kHz LF wake-up pulse, then listens on 315/433 MHz
 * for the smart key's response. Beeps faster as signal gets stronger.
 *
 * Hardware: ESP32 DevKit + CC1101 module + 125kHz coil + buzzer + LEDs
 */

#include <SPI.h>

// --- Pin Definitions ---
#define CC1101_CS     5
#define CC1101_GDO0   2

#define LF_COIL_PIN  25   // MOSFET gate driving 125kHz coil
#define BUZZER_PIN   26
#define LED_GREEN    32
#define LED_YELLOW   33
#define LED_RED      27
#define SCAN_BUTTON   4

// --- CC1101 Register Addresses ---
#define CC1101_SRES    0x30
#define CC1101_SRX     0x34
#define CC1101_SIDLE   0x36
#define CC1101_RSSI    0x34  // Status register
#define CC1101_MARCSTATE 0x35

// --- Configuration ---
// Set this to match your region:
//   315000000 for North America
//   433920000 for Europe/Asia
#define TARGET_FREQ_HZ  315000000UL

#define LF_WAKE_DURATION_MS  50    // How long to pulse the 125kHz signal
#define LF_HALF_PERIOD_US    4     // ~125kHz = 8us period
#define SCAN_LISTEN_MS       200   // How long to listen for a response
#define RSSI_NOISE_FLOOR    -90    // dBm, signals below this are noise
#define RSSI_STRONG         -40    // dBm, signals above this = very close

// --- CC1101 SPI Helpers ---

void cc1101_write_reg(uint8_t addr, uint8_t value) {
    digitalWrite(CC1101_CS, LOW);
    SPI.transfer(addr);
    SPI.transfer(value);
    digitalWrite(CC1101_CS, HIGH);
}

uint8_t cc1101_read_status(uint8_t addr) {
    digitalWrite(CC1101_CS, LOW);
    SPI.transfer(addr | 0xC0);  // Status read burst
    uint8_t val = SPI.transfer(0);
    digitalWrite(CC1101_CS, HIGH);
    return val;
}

void cc1101_strobe(uint8_t strobe) {
    digitalWrite(CC1101_CS, LOW);
    SPI.transfer(strobe);
    digitalWrite(CC1101_CS, HIGH);
}

void cc1101_reset() {
    digitalWrite(CC1101_CS, HIGH);
    delayMicroseconds(30);
    digitalWrite(CC1101_CS, LOW);
    delayMicroseconds(30);
    digitalWrite(CC1101_CS, HIGH);
    delayMicroseconds(45);
    cc1101_strobe(CC1101_SRES);
    delay(10);
}

// --- CC1101 Configuration for 315 MHz or 433 MHz ---

void cc1101_configure() {
    // Frequency registers for 315 MHz
    // FREQ = (desired_freq / 26MHz_crystal) * 2^16
    // For 315 MHz: FREQ = 0x0C1D89
    // For 433.92 MHz: FREQ = 0x10A762

    uint32_t freq_word;
    if (TARGET_FREQ_HZ > 400000000UL) {
        freq_word = 0x10A762;  // 433.92 MHz
    } else {
        freq_word = 0x0C1D89;  // 315 MHz
    }

    cc1101_write_reg(0x0D, (freq_word >> 16) & 0xFF);  // FREQ2
    cc1101_write_reg(0x0E, (freq_word >> 8) & 0xFF);   // FREQ1
    cc1101_write_reg(0x0F, freq_word & 0xFF);           // FREQ0

    // Modem config: OOK modulation, wide bandwidth for detection
    cc1101_write_reg(0x10, 0x07);  // MDMCFG4 - RX BW ~325kHz
    cc1101_write_reg(0x11, 0x32);  // MDMCFG3 - data rate (doesn't matter much for RSSI-only)
    cc1101_write_reg(0x12, 0x30);  // MDMCFG2 - OOK, no sync
    cc1101_write_reg(0x15, 0x00);  // DEVIATN

    // AGC settings for good RSSI readings
    cc1101_write_reg(0x1B, 0x07);  // AGCCTRL2
    cc1101_write_reg(0x1C, 0x00);  // AGCCTRL1
    cc1101_write_reg(0x1D, 0x91);  // AGCCTRL0
}

int8_t cc1101_get_rssi_dbm() {
    uint8_t raw = cc1101_read_status(CC1101_RSSI);
    int16_t rssi;
    if (raw >= 128) {
        rssi = (int16_t)(raw - 256) / 2 - 74;
    } else {
        rssi = raw / 2 - 74;
    }
    return (int8_t)rssi;
}

// --- 125 kHz LF Wake-up Pulse ---

void send_lf_wake_pulse() {
    // Generate a 125 kHz square wave on the coil pin
    // This mimics the car's LF antenna to wake the smart key
    unsigned long start = millis();
    while (millis() - start < LF_WAKE_DURATION_MS) {
        digitalWrite(LF_COIL_PIN, HIGH);
        delayMicroseconds(LF_HALF_PERIOD_US);
        digitalWrite(LF_COIL_PIN, LOW);
        delayMicroseconds(LF_HALF_PERIOD_US);
    }
}

// --- Feedback (Buzzer + LEDs) ---

void set_proximity_feedback(int8_t rssi_dbm) {
    // Map RSSI to proximity level 0-3
    int level = 0;
    if (rssi_dbm > RSSI_STRONG) {
        level = 3;  // Very close
    } else if (rssi_dbm > -60) {
        level = 2;  // Nearby
    } else if (rssi_dbm > RSSI_NOISE_FLOOR) {
        level = 1;  // Detected but far
    }

    // LEDs
    digitalWrite(LED_GREEN,  level >= 1 ? HIGH : LOW);
    digitalWrite(LED_YELLOW, level >= 2 ? HIGH : LOW);
    digitalWrite(LED_RED,    level >= 3 ? HIGH : LOW);

    // Buzzer beep rate
    if (level == 0) {
        noTone(BUZZER_PIN);
    } else if (level == 1) {
        tone(BUZZER_PIN, 1000, 50);  // Slow beep
    } else if (level == 2) {
        tone(BUZZER_PIN, 2000, 50);  // Medium beep
    } else {
        tone(BUZZER_PIN, 3000, 50);  // Fast/high beep
    }
}

void clear_feedback() {
    noTone(BUZZER_PIN);
    digitalWrite(LED_GREEN, LOW);
    digitalWrite(LED_YELLOW, LOW);
    digitalWrite(LED_RED, LOW);
}

// --- Main ---

void setup() {
    Serial.begin(115200);
    Serial.println("Car Key Finder starting...");

    // Pin modes
    pinMode(CC1101_CS, OUTPUT);
    pinMode(CC1101_GDO0, INPUT);
    pinMode(LF_COIL_PIN, OUTPUT);
    pinMode(BUZZER_PIN, OUTPUT);
    pinMode(LED_GREEN, OUTPUT);
    pinMode(LED_YELLOW, OUTPUT);
    pinMode(LED_RED, OUTPUT);
    pinMode(SCAN_BUTTON, INPUT_PULLUP);

    digitalWrite(LF_COIL_PIN, LOW);

    // Init SPI and CC1101
    SPI.begin();
    cc1101_reset();
    cc1101_configure();

    // Startup blink
    for (int i = 0; i < 3; i++) {
        digitalWrite(LED_GREEN, HIGH);
        delay(100);
        digitalWrite(LED_GREEN, LOW);
        delay(100);
    }

    Serial.println("Ready. Press button to scan.");
}

void loop() {
    // Wait for button press
    if (digitalRead(SCAN_BUTTON) == LOW) {
        delay(50);  // Debounce
        if (digitalRead(SCAN_BUTTON) == LOW) {
            scan_for_key();
        }
        // Wait for button release
        while (digitalRead(SCAN_BUTTON) == LOW) {
            delay(10);
        }
    }
}

void scan_for_key() {
    Serial.println("Scanning...");

    // Step 1: Send 125 kHz wake-up pulse
    send_lf_wake_pulse();

    // Step 2: Switch CC1101 to RX mode and listen
    cc1101_strobe(CC1101_SIDLE);
    delay(1);
    cc1101_strobe(CC1101_SRX);
    delay(5);  // Let AGC settle

    // Step 3: Sample RSSI over the listen window
    int8_t peak_rssi = -128;
    unsigned long listen_start = millis();

    while (millis() - listen_start < SCAN_LISTEN_MS) {
        int8_t rssi = cc1101_get_rssi_dbm();
        if (rssi > peak_rssi) {
            peak_rssi = rssi;
        }
        delayMicroseconds(500);
    }

    // Step 4: Back to idle
    cc1101_strobe(CC1101_SIDLE);

    // Step 5: Report
    Serial.printf("Peak RSSI: %d dBm\n", peak_rssi);

    if (peak_rssi > RSSI_NOISE_FLOOR) {
        Serial.println("Key detected!");
        set_proximity_feedback(peak_rssi);
        delay(1000);
    } else {
        Serial.println("No key detected.");
        // Single low beep to indicate "nothing found"
        tone(BUZZER_PIN, 400, 200);
        delay(300);
    }

    clear_feedback();
}
