/*
 * ============================================================
 *  Smart Ambulance Priority Traffic System — ESP32 Firmware
 *  VKIT Hackathon | Powered by Robomanthan Pvt Ltd
 * ============================================================
 *
 *  Hardware:
 *    - Green LED  → GPIO 5
 *    - Red LED    → GPIO 4
 *    - Active Buzzer → GPIO 2
 *    - L298N IN1  → GPIO 18   (motor direction)
 *    - L298N IN2  → GPIO 19   (motor direction)
 *    - L298N ENA  → GPIO 21   (motor enable / speed)
 *
 *  HTTP endpoints (port 80):
 *    POST /move   → Green LED ON, Motor fwd, buzzer 2 sec
 *    POST /stop   → Red LED ON,   Motor OFF, buzzer 10 sec
 *    POST /yellow → Red LED blink, buzzer 200 ms short beep
 *    POST /idle   → Everything OFF
 *    GET  /status → {"state":"MOVE|STOP|YELLOW|IDLE"}
 *
 *  After boot, IP address is printed to Serial.
 *  Copy that IP into app.py → ESP32_IP.
 * ============================================================
 */

#include <Arduino.h>
#include <WiFi.h>
#include <WebServer.h>

// ── WiFi credentials ────────────────────────────────────────
const char* WIFI_SSID     = "";      // ← change this
const char* WIFI_PASSWORD = "12345688";   // ← change this

// ── GPIO pins ────────────────────────────────────────────────
#define PIN_LED_GREEN   5
#define PIN_LED_RED     4
#define PIN_BUZZER      2
#define PIN_MOTOR_IN1   18
#define PIN_MOTOR_IN2   19
#define PIN_MOTOR_EN    21   // L298N ENA pin

WebServer server(80);
String currentState = "IDLE";

// ── Non-blocking buzzer timer ────────────────────────────────
//    RED=10 000 ms | GREEN=2 000 ms | YELLOW=200 ms
bool buzzerActive       = false;
unsigned long buzzerOffTime = 0;

// ── Helper: CORS header for Flask proxy calls ────────────────
void addCORS() {
  server.sendHeader("Access-Control-Allow-Origin", "*");
  server.sendHeader("Access-Control-Allow-Methods", "GET,POST,OPTIONS");
  server.sendHeader("Access-Control-Allow-Headers", "Content-Type");
}

// ── Hardware actions ─────────────────────────────────────────
void allOff() {
  digitalWrite(PIN_LED_GREEN, LOW);
  digitalWrite(PIN_LED_RED,   LOW);
  digitalWrite(PIN_BUZZER,    LOW);
  digitalWrite(PIN_MOTOR_IN1, LOW);
  digitalWrite(PIN_MOTOR_IN2, LOW);
  digitalWrite(PIN_MOTOR_EN,  LOW);
}

void doMove() {
  allOff();
  digitalWrite(PIN_LED_GREEN, HIGH);
  // Motor forward: IN1=HIGH, IN2=LOW, ENA=HIGH
  digitalWrite(PIN_MOTOR_IN1, HIGH);
  digitalWrite(PIN_MOTOR_IN2, LOW);
  digitalWrite(PIN_MOTOR_EN,  HIGH);
  Serial.println("[Motor] IN1=HIGH IN2=LOW ENA=HIGH — should be spinning");
  // GREEN → 2-second non-blocking beep
  digitalWrite(PIN_BUZZER, HIGH);
  buzzerActive  = true;
  buzzerOffTime = millis() + 2000;
  currentState  = "MOVE";
  Serial.println("[ESP32] State → MOVE");
}

void doStop() {
  allOff();
  digitalWrite(PIN_LED_RED, HIGH);
  // RED → 10-second non-blocking beep
  digitalWrite(PIN_BUZZER, HIGH);
  buzzerActive  = true;
  buzzerOffTime = millis() + 10000;
  currentState  = "STOP";
  Serial.println("[ESP32] State → STOP");
}

void doYellow() {
  allOff();
  // YELLOW → 200 ms short beep only
  digitalWrite(PIN_BUZZER, HIGH);
  buzzerActive  = true;
  buzzerOffTime = millis() + 200;
  currentState  = "YELLOW";
  Serial.println("[ESP32] State → YELLOW");
}

void doIdle() {
  buzzerActive = false;              // cancel any timed beep
  allOff();
  currentState = "IDLE";
  Serial.println("[ESP32] State → IDLE");
}

// ── Motor self-test (call from setup to verify wiring) ─────────
void motorSelfTest() {
  Serial.println("[Motor] Self-test START — motor should spin for 1.5s");
  digitalWrite(PIN_MOTOR_IN1, HIGH);
  digitalWrite(PIN_MOTOR_IN2, LOW);
  digitalWrite(PIN_MOTOR_EN,  HIGH);
  delay(1500);
  digitalWrite(PIN_MOTOR_IN1, LOW);
  digitalWrite(PIN_MOTOR_EN,  LOW);
  Serial.println("[Motor] Self-test END");
}

// ── HTTP handlers ─────────────────────────────────────────────
void handleOptions() {
  addCORS();
  server.send(204, "text/plain", "");
}

void handleMove() {
  doMove();
  addCORS();
  server.send(200, "application/json", "{\"status\":\"ok\",\"state\":\"MOVE\"}");
}

void handleStop() {
  doStop();
  addCORS();
  server.send(200, "application/json", "{\"status\":\"ok\",\"state\":\"STOP\"}");
}

void handleYellow() {
  doYellow();
  addCORS();
  server.send(200, "application/json", "{\"status\":\"ok\",\"state\":\"YELLOW\"}");
}

void handleIdle() {
  doIdle();
  addCORS();
  server.send(200, "application/json", "{\"status\":\"ok\",\"state\":\"IDLE\"}");
}

void handleStatus() {
  addCORS();
  String json = "{\"status\":\"ok\",\"state\":\"" + currentState + "\"}";
  server.send(200, "application/json", json);
}

void handleNotFound() {
  server.send(404, "application/json", "{\"error\":\"not found\"}");
}

void handleTestMotor() {
  motorSelfTest();
  addCORS();
  server.send(200, "application/json", "{\"status\":\"ok\",\"message\":\"Motor test ran for 1.5s\"}");
}

// ── Setup ─────────────────────────────────────────────────────
void setup() {
  Serial.begin(115200);
  delay(100);

  // Pin modes
  pinMode(PIN_LED_GREEN, OUTPUT);
  pinMode(PIN_LED_RED,   OUTPUT);
  pinMode(PIN_BUZZER,    OUTPUT);
  pinMode(PIN_MOTOR_IN1, OUTPUT);
  pinMode(PIN_MOTOR_IN2, OUTPUT);
  pinMode(PIN_MOTOR_EN,  OUTPUT);
  allOff();

  // Connect to WiFi
  Serial.printf("\nConnecting to %s", WIFI_SSID);
  WiFi.mode(WIFI_STA);
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);

  int attempts = 0;
  while (WiFi.status() != WL_CONNECTED && attempts < 30) {
    delay(500);
    Serial.print(".");
    attempts++;
  }

  if (WiFi.status() == WL_CONNECTED) {
    Serial.println("\n✅ WiFi connected!");
    Serial.print("📡 ESP32 IP Address: ");
    Serial.println(WiFi.localIP());
    Serial.println("👉 Copy this IP into app.py → ESP32_IP");

    // Blink green LED twice to indicate successful boot
    for (int i = 0; i < 2; i++) {
      digitalWrite(PIN_LED_GREEN, HIGH); delay(200);
      digitalWrite(PIN_LED_GREEN, LOW);  delay(200);
    }

    // ✔ Motor self-test — motor MUST spin here; if it doesn't, check wiring
    motorSelfTest();
  } else {
    Serial.println("\n❌ WiFi connection FAILED. Check credentials.");
    // Blink red LED to show failure
    for (int i = 0; i < 5; i++) {
      digitalWrite(PIN_LED_RED, HIGH); delay(150);
      digitalWrite(PIN_LED_RED, LOW);  delay(150);
    }
  }

  // Register HTTP routes
  server.on("/move",       HTTP_POST,    handleMove);
  server.on("/stop",       HTTP_POST,    handleStop);
  server.on("/yellow",     HTTP_POST,    handleYellow);
  server.on("/idle",       HTTP_POST,    handleIdle);
  server.on("/test_motor", HTTP_POST,    handleTestMotor);
  server.on("/status",     HTTP_GET,     handleStatus);
  server.on("/move",       HTTP_OPTIONS, handleOptions);
  server.on("/stop",       HTTP_OPTIONS, handleOptions);
  server.on("/yellow",     HTTP_OPTIONS, handleOptions);
  server.on("/idle",       HTTP_OPTIONS, handleOptions);
  server.onNotFound(handleNotFound);

  server.begin();
  Serial.println("🚦 HTTP server started on port 80");
}

// ── Loop ──────────────────────────────────────────────────────
void loop() {
  server.handleClient();

  // Non-blocking buzzer shutoff (RED=10s, GREEN=2s, YELLOW=200ms)
  if (buzzerActive && millis() >= buzzerOffTime) {
    digitalWrite(PIN_BUZZER, LOW);
    buzzerActive = false;
  }
}
