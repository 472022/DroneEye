// DroneEye AI - ESP32 Sensor Sender
// Board: ESP32 Dev Module | Upload speed: 115200
// Libraries: ArduinoJson v7, DallasTemperature, OneWire, TinyGPSPlus

#include <WiFi.h>
#include <HTTPClient.h>
#include <ArduinoJson.h>
#include <OneWire.h>
#include <DallasTemperature.h>
#include <TinyGPSPlus.h>

// CONFIGURE THESE
const char* WIFI_SSID     = "YOUR_WIFI_SSID";
const char* WIFI_PASSWORD = "YOUR_WIFI_PASSWORD";
const char* SERVER_URL    = "http://YOUR_LAPTOP_IP:5000/api/data";
const int   SEND_INTERVAL = 2000;  // ms

// PIN MAP
#define PIN_VOLTAGE   34
#define PIN_CURRENT   35
#define PIN_TEMP       4
#define PIN_VIBRATION  5
#define GPS_RX_PIN    16
#define GPS_TX_PIN    17

// OBJECTS
OneWire           oneWire(PIN_TEMP);
DallasTemperature tempSensor(&oneWire);
HardwareSerial    gpsSerial(2);
TinyGPSPlus       gps;

// CALIBRATION (adjust for your hardware)
const float VOLTAGE_SCALE = 15.0 / 4095.0;   // ZMPT101B: 4095 ADC = 15kV
const float CURRENT_OFFSET = 1.65;           // ACS712: 0A = 1.65V (3.3V ref)
const float CURRENT_SENSITIVITY = 0.0660;    // ACS712 20A: 0.185V/A scaled

float readVoltage() {
  return analogRead(PIN_VOLTAGE) * VOLTAGE_SCALE;
}

float readCurrent() {
  float volts = analogRead(PIN_CURRENT) * (3.3 / 4095.0);
  float current = (volts - CURRENT_OFFSET) / CURRENT_SENSITIVITY;
  return fabs(current);
}

float readTemperature() {
  tempSensor.requestTemperatures();
  float t = tempSensor.getTempCByIndex(0);
  return (t == DEVICE_DISCONNECTED_C) ? -99.0 : t;
}

bool readVibration() {
  return !digitalRead(PIN_VIBRATION);  // INPUT_PULLUP inverted
}

void setup() {
  Serial.begin(115200);
  analogReadResolution(12);
  analogSetAttenuation(ADC_11db);
  tempSensor.begin();
  gpsSerial.begin(9600, SERIAL_8N1, GPS_RX_PIN, GPS_TX_PIN);
  pinMode(PIN_VIBRATION, INPUT_PULLUP);

  Serial.print("Connecting to WiFi");
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
  int tries = 0;
  while (WiFi.status() != WL_CONNECTED && tries < 30) {
    delay(500);
    Serial.print(".");
    tries++;
  }

  if (WiFi.status() == WL_CONNECTED) {
    Serial.println("\nWiFi connected: " + WiFi.localIP().toString());
    Serial.println("Sending to: " + String(SERVER_URL));
  } else {
    Serial.println("\n[ERROR] WiFi connection failed!");
  }
}

void loop() {
  while (gpsSerial.available()) gps.encode(gpsSerial.read());

  static unsigned long lastSend = 0;
  if (millis() - lastSend < SEND_INTERVAL) return;
  lastSend = millis();

  float v = readVoltage();
  float i = readCurrent();
  float t = readTemperature();
  bool vib = readVibration();
  float lat = gps.location.isValid() ? gps.location.lat() : 0.0;
  float lng = gps.location.isValid() ? gps.location.lng() : 0.0;

  JsonDocument doc;
  doc["v"] = round(v * 100) / 100.0;
  doc["i"] = round(i * 100) / 100.0;
  doc["t"] = round(t * 10) / 10.0;
  doc["vib"] = vib ? 1 : 0;
  doc["lat"] = lat;
  doc["lng"] = lng;

  String payload;
  serializeJson(doc, payload);

  if (WiFi.status() == WL_CONNECTED) {
    HTTPClient http;
    http.begin(SERVER_URL);
    http.addHeader("Content-Type", "application/json");
    int code = http.POST(payload);

    Serial.printf(
      "[%lus] v=%.2f i=%.2f t=%.1fC vib=%d lat=%.4f lng=%.4f -> HTTP %d\n",
      millis() / 1000,
      v,
      i,
      t,
      vib,
      lat,
      lng,
      code
    );

    http.end();
  } else {
    Serial.println("[WARN] WiFi disconnected - attempting reconnect...");
    WiFi.reconnect();
  }
}
