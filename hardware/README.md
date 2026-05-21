# ESP32 Starter Code

This folder contains starter code for programming ESP32 microcontrollers.

## Hardware Required

- ESP32 development board (e.g., ESP32-DevKitC, ESP32-WROOM-32, etc.)
- USB cable (typically micro-USB or USB-C depending on your board)

## Software Setup

### Option 1: Arduino IDE

1. **Install Arduino IDE**
   - Download from: https://www.arduino.cc/en/software

2. **Install ESP32 Board Support**
   - Open Arduino IDE
   - Go to `File` → `Preferences`
   - Add this URL to "Additional Board Manager URLs":
     ```
     https://raw.githubusercontent.com/espressif/arduino-esp32/gh-pages/package_esp32_index.json
     ```
   - Go to `Tools` → `Board` → `Board Manager`
   - Search for "esp32" and install "esp32 by Espressif Systems"

3. **Select Your Board**
   - Go to `Tools` → `Board` → `ESP32 Arduino`
   - Select your specific ESP32 board model

4. **Select Port**
   - Go to `Tools` → `Port`
   - Select the COM port where your ESP32 is connected

### Option 2: PlatformIO

1. **Install PlatformIO**
   - Install VS Code: https://code.visualstudio.com/
   - Install PlatformIO extension from VS Code marketplace

2. **Create New Project**
   - Click "PlatformIO Home" → "New Project"
   - Select your ESP32 board
   - Choose "Arduino" framework

3. **Use the starter code**
   - Copy `esp32_starter.cpp` to your `src/` folder
   - Build and upload

## Getting Started

1. **Open the starter code**
   - Open `esp32_starter.cpp` in your IDE

2. **Upload to ESP32**
   - Connect your ESP32 to your computer via USB
   - Click the Upload button (→) in Arduino IDE or PlatformIO

3. **Monitor Serial Output**
   - Open Serial Monitor (`Tools` → `Serial Monitor` in Arduino IDE)
   - Set baud rate to 115200
   - You should see the ESP32 initialization messages and LED blink status

## What's Included

The starter code includes:
- Basic setup and loop structure
- Serial communication initialization
- Built-in LED blinking example
- ESP32 chip information display
- Comments and documentation for easy understanding

## Next Steps

After getting the starter code working, you can explore:
- Wi-Fi connectivity (Station and Access Point modes)
- Bluetooth communication
- Sensor interfacing (I2C, SPI, ADC)
- PWM for motor control or LED dimming
- Web server creation
- MQTT for IoT applications
- Deep sleep for battery-powered projects

## Troubleshooting

**Upload fails:**
- Hold the BOOT button while uploading
- Check the correct COM port is selected
- Try a different USB cable or port
- Install USB drivers (CP210x or CH340 depending on your board)

**Serial Monitor shows gibberish:**
- Make sure baud rate is set to 115200

**Board not detected:**
- Install appropriate USB drivers:
  - CP210x: https://www.silabs.com/developers/usb-to-uart-bridge-vcp-drivers
  - CH340: http://www.wch-ic.com/downloads/CH341SER_EXE.html

## Resources

- [ESP32 Official Documentation](https://docs.espressif.com/projects/esp-idf/en/latest/esp32/)
- [Arduino ESP32 Core](https://github.com/espressif/arduino-esp32)
- [ESP32 Pinout Reference](https://randomnerdtutorials.com/esp32-pinout-reference-gpios/)
- [Random Nerd Tutorials - ESP32](https://randomnerdtutorials.com/getting-started-with-esp32/)
