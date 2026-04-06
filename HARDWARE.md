# 🚦 Smart Ambulance Priority Traffic System — Hardware Connection Guide

This document outlines the complete hardware setup for the ESP32-based traffic control system. The system uses an **ESP32** to control LEDs, a buzzer, and a DC motor via an **L293D** motor driver.

## 🛠 Component List
1.  **ESP32 Development Board** (30-pin or 38-pin version)
2.  **L293D Motor Driver IC** (or L293D Motor Shield)
3.  **DC Motor** (for traffic gate or vehicle simulation)
4.  **Red LED** & **Green LED**
5.  **Active Buzzer**
6.  **Resistors** (220Ω for LEDs)
7.  **External Power Supply** (6V–12V for the motor, if needed)
8.  **Breadboard & Jumper Wires**

---

## 🔌 Pin Mapping Table

| Component | ESP32 Pin (GPIO) | Description |
| :--- | :--- | :--- |
| **Green LED** | `GPIO 5` | Status: MOVE (Signal is Green) |
| **Red LED** | `GPIO 4` | Status: STOP (Signal is Red / Ambulance) |
| **Active Buzzer** | `GPIO 2` | Audio Alerts (Short beeps for MOVE, Sustained for STOP) |
| **L293D EN (Enable)** | `GPIO 21` | Motor Speed / Enable (PWM capable) |
| **L293D IN1** | `GPIO 18` | Motor Direction Control 1 |
| **L293D IN2** | `GPIO 19` | Motor Direction Control 2 |

---

## 📐 Detailed Wiring Instructions

### 1. LEDs & Buzzer
*   **Green LED**: Connect Anode (+) to `GPIO 5` (via 220Ω resistor) and Cathode (-) to `GND`.
*   **Red LED**: Connect Anode (+) to `GPIO 4` (via 220Ω resistor) and Cathode (-) to `GND`.
*   **Buzzer**: Connect Positive (+) to `GPIO 2` and Negative (-) to `GND`.

### 2. L293D Motor Driver Connections
*   **L293D Pin 1 (Enable 1,2)** → `ESP32 GPIO 21`
*   **L293D Pin 2 (Input 1)** → `ESP32 GPIO 18`
*   **L293D Pin 7 (Input 2)** → `ESP32 GPIO 19`
*   **L293D Pin 3 (Output 1)** → `DC Motor Terminal 1`
*   **L293D Pin 6 (Output 2)** → `DC Motor Terminal 2`
*   **L293D Pin 4, 5, 12, 13** → `GND` (Common Ground with ESP32)
*   **L293D Pin 16 (VCC1 / Logic High)** → `ESP32 3.3V or 5V`
*   **L293D Pin 8 (VCC2 / Motor Power)** → `External Battery (+) 6V-12V` (Connect Battery GND to ESP32 GND)

---

## ⚡ Power Requirements
*   The **ESP32** can be powered via USB.
*   The **DC Motor** should ideally be powered by an external source (e.g., 9V battery) connected to the L293D Pin 8 to prevent noise or brownouts on the ESP32.
*   **Crucial**: Always ensure a **Common Ground** between the ESP32, the L293D, and any external batteries.

---

## 📝 Verification
1.  Upload the `firmware/esp32_traffic.ino` to your ESP32.
2.  Open the Serial Monitor (115200 baud).
3.  Once connected to WiFi, the Green LED should blink twice.
4.  Use the Web UI "Manual Override" buttons to test:
    *   **MOVE**: Green LED ON + Motor Rotates + Short Beeps.
    *   **STOP**: Red LED ON + Motor Stops + Sustained Beep.
    *   **IDLE**: Everything OFF.
