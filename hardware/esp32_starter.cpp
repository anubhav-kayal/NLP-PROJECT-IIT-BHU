/*
 * ESP32 Starter Code
 * 
 * This is a basic starter template for ESP32 microcontroller programming.
 * The ESP32 is a powerful, low-cost microcontroller with built-in Wi-Fi and Bluetooth.
 * 
 * Hardware Requirements:
 * - ESP32 development board
 * - USB cable for programming and power
 * 
 * Setup Instructions:
 * 1. Install Arduino IDE or PlatformIO
 * 2. Install ESP32 board support
 * 3. Select your ESP32 board from Tools > Board menu
 * 4. Select the correct COM port
 * 5. Upload the code
 */

#include <Arduino.h>

// Pin definitions
#define LED_PIN 2  // Built-in LED on most ESP32 boards

// Global variables
unsigned long previousMillis = 0;
const long interval = 1000;  // Blink interval in milliseconds

// Function prototypes
void setup();
void loop();
void blinkLED();

/**
 * Setup function - runs once when the ESP32 starts
 * Initialize pins, serial communication, and peripherals here
 */
void setup() {
  // Initialize serial communication at 115200 baud
  Serial.begin(115200);
  
  // Wait for serial port to connect
  delay(1000);
  
  Serial.println("ESP32 Starter Code");
  Serial.println("==================");
  Serial.println("ESP32 initialized successfully!");
  
  // Initialize the LED pin as an output
  pinMode(LED_PIN, OUTPUT);
  
  // Print ESP32 chip information
  Serial.print("Chip Model: ");
  Serial.println(ESP.getChipModel());
  Serial.print("Chip Revision: ");
  Serial.println(ESP.getChipRevision());
  Serial.print("Number of Cores: ");
  Serial.println(ESP.getChipCores());
  Serial.print("CPU Frequency: ");
  Serial.print(ESP.getCpuFreqMHz());
  Serial.println(" MHz");
  Serial.print("Flash Size: ");
  Serial.print(ESP.getFlashChipSize() / (1024 * 1024));
  Serial.println(" MB");
  Serial.println();
}

/**
 * Main loop function - runs repeatedly
 * Add your main program logic here
 */
void loop() {
  // Get current time
  unsigned long currentMillis = millis();
  
  // Blink LED every interval
  if (currentMillis - previousMillis >= interval) {
    previousMillis = currentMillis;
    blinkLED();
  }
  
  // Add your custom code here
  // Example: Read sensors, process data, communicate over Wi-Fi/Bluetooth, etc.
  
  // Small delay to prevent watchdog timer issues
  delay(10);
}

/**
 * Blink the built-in LED
 */
void blinkLED() {
  static bool ledState = false;
  ledState = !ledState;
  digitalWrite(LED_PIN, ledState);
  
  if (ledState) {
    Serial.println("LED ON");
  } else {
    Serial.println("LED OFF");
  }
}

/*
 * Additional Resources:
 * - ESP32 Documentation: https://docs.espressif.com/projects/esp-idf/en/latest/esp32/
 * - Arduino ESP32 Core: https://github.com/espressif/arduino-esp32
 * - ESP32 Pinout Reference: https://randomnerdtutorials.com/esp32-pinout-reference-gpios/
 * 
 * Common ESP32 Features to Explore:
 * - Wi-Fi connectivity (Station and Access Point modes)
 * - Bluetooth Classic and BLE
 * - ADC for analog sensor reading
 * - PWM for motor control or LED dimming
 * - I2C and SPI communication
 * - Touch sensors
 * - Deep sleep mode for low power applications
 */
