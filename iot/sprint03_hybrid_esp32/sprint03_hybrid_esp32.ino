#include <Adafruit_GFX.h>
#include <Adafruit_MPU6050.h>
#include <Adafruit_SSD1306.h>
#include <Adafruit_Sensor.h>
#include <HTTPClient.h>
#include <PubSubClient.h>
#include <WiFi.h>
#include <WiFiClientSecure.h>
#include <Wire.h>

// CarePlus Sprint 03 - ESP32 hibrido
// FIWARE/MQTT guarda telemetria e historico.
// Render/FastAPI atualiza o app quando a missao e validada.

const char* ssid = "Wokwi-GUEST";
const char* password = "";

const char* mqttServer = "35.198.7.130";
const int mqttPort = 1883;
const char* mqttTopic = "/TEF/token001/attrs";

const char* renderTokenCollectedUrl =
  "https://careplus-sprint3-umkto.onrender.com/iot/token-collected";

const char* deviceId = "careplus-token-001";

const int buttonPin = 18;
const int greenLedPin = 19;
const int redLedPin = 21;
const int buzzerPin = 23;

const int oledSdaPin = 25;
const int oledSclPin = 26;
const int mpuSdaPin = 32;
const int mpuSclPin = 33;

#define SCREEN_WIDTH 128
#define SCREEN_HEIGHT 64
#define OLED_RESET -1

TwoWire mpuWire = TwoWire(1);
Adafruit_SSD1306 display(SCREEN_WIDTH, SCREEN_HEIGHT, &Wire, OLED_RESET);
Adafruit_MPU6050 mpu;

WiFiClient mqttWifiClient;
WiFiClientSecure renderSecureClient;
PubSubClient mqttClient(mqttWifiClient);

const int pointsPerStep = 1;
const float stepThreshold = 0.23;
const unsigned long minStepInterval = 320;
const unsigned long sensorInterval = 150;
const unsigned long telemetryInterval = 30000;
const unsigned long mqttReconnectInterval = 5000;
const unsigned long debounceDelay = 700;

int validationCount = 0;
int steps = 0;
int pendingSteps = 0;
int tokenValue = 0;
int totalPoints = 0;
int batteryLevel = 100;

float lastAx = 0;
float lastAy = 0;
float lastAz = 0;
float lastMagnitudeG = 1.0;
bool stepArmed = true;
bool mqttWasConnected = false;

unsigned long lastStepTime = 0;
unsigned long lastSensorRead = 0;
unsigned long lastTelemetryPublish = 0;
unsigned long lastPressTime = 0;
unsigned long lastMqttReconnectAttempt = 0;

void beepSuccess() {
  tone(buzzerPin, 1200, 130);
  delay(170);
  tone(buzzerPin, 1600, 150);
}

void beepError() {
  tone(buzzerPin, 320, 350);
}

void setFeedback(bool successOn, bool errorOn) {
  digitalWrite(greenLedPin, successOn ? HIGH : LOW);
  digitalWrite(redLedPin, errorOn ? HIGH : LOW);
}

void clearDisplayBase() {
  display.clearDisplay();
  display.setTextColor(SSD1306_WHITE);
  display.setTextSize(1);
  display.setCursor(0, 0);
}

void showBootScreen(const char* line) {
  clearDisplayBase();
  display.println("CarePlus S03");
  display.println("----------------");
  display.println(line);
  display.display();
}

void showTrackingScreen() {
  clearDisplayBase();
  display.println(pendingSteps > 0 ? "Pronto validar" : "Monitorando");
  display.println("----------------");
  display.print("Passos: ");
  display.println(steps);
  display.print("Pendentes: ");
  display.println(pendingSteps);
  display.print("Pontos: ");
  display.println(totalPoints);
  display.print("Bateria: ");
  display.print(batteryLevel);
  display.println("%");
  display.println();
  display.println("Botao valida");
  display.display();
}

void showStatusScreen(const char* title, const char* detail) {
  clearDisplayBase();
  display.println(title);
  display.println("----------------");
  display.println(detail);
  display.display();
}

void logPrefix() {
  Serial.print("[");
  Serial.print(millis() / 1000);
  Serial.print("s] ");
}

void logInfo(const String& message) {
  logPrefix();
  Serial.println(message);
}

String activityLevel() {
  if (pendingSteps >= 30) return "high";
  if (pendingSteps >= 10) return "moderate";
  if (pendingSteps > 0) return "light";
  return "idle";
}

String currentFlowState() {
  if (pendingSteps > 0) return "ready_to_validate";
  return "tracking";
}

String buildFiwarePayload(const String& state, int eventPoints) {
  String payload = "s|" + state;
  payload += "|p|" + String(validationCount);
  payload += "|st|" + String(steps);
  payload += "|ps|" + String(pendingSteps);
  payload += "|v|" + String(eventPoints);
  payload += "|tp|" + String(totalPoints);
  payload += "|b|" + String(batteryLevel);
  payload += "|r|" + String(WiFi.RSSI());
  payload += "|al|" + activityLevel();
  payload += "|ax|" + String(lastAx, 2);
  payload += "|ay|" + String(lastAy, 2);
  payload += "|az|" + String(lastAz, 2);
  return payload;
}

void connectWiFi() {
  WiFi.mode(WIFI_STA);
  WiFi.begin(ssid, password);
  showBootScreen("Conectando Wi-Fi");
  logInfo("Conectando ao Wi-Fi...");

  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }

  Serial.println();
  logInfo("Wi-Fi conectado.");
  Serial.print("IP: ");
  Serial.println(WiFi.localIP());
}

bool connectMQTT(bool showDetails = true) {
  if (mqttClient.connected()) return true;

  if (showDetails) {
    showBootScreen("Conectando MQTT");
    logInfo("Conectando ao Mosquitto/FIWARE...");
  }

  String clientId = "careplus-sprint03-";
  clientId += String(random(0xffff), HEX);

  bool connected = mqttClient.connect(clientId.c_str());
  mqttWasConnected = connected;

  if (connected) {
    logInfo("MQTT conectado.");
    return true;
  }

  logPrefix();
  Serial.print("Falha MQTT. Codigo: ");
  Serial.println(mqttClient.state());
  return false;
}

void publishFiwareTelemetry(const String& state, int eventPoints) {
  if (!mqttClient.connected() && !connectMQTT(false)) {
    showStatusScreen("Erro MQTT", "Telemetria nao enviada");
    logInfo("FIWARE/MQTT indisponivel.");
    return;
  }

  String payload = buildFiwarePayload(state, eventPoints);
  bool published = mqttClient.publish(mqttTopic, payload.c_str());

  Serial.println();
  Serial.println("========== FIWARE MQTT ==========");
  Serial.print("Topico: ");
  Serial.println(mqttTopic);
  Serial.print("Payload: ");
  Serial.println(payload);
  Serial.println("=================================");

  logInfo(published ? "Telemetria publicada no FIWARE." : "Falha ao publicar no FIWARE.");
}

bool notifyRenderTokenCollected(int points) {
  if (WiFi.status() != WL_CONNECTED) {
    connectWiFi();
  }

  HTTPClient http;
  http.begin(renderSecureClient, renderTokenCollectedUrl);
  http.addHeader("Content-Type", "application/json");

  String body = "{";
  body += "\"device_id\":\"" + String(deviceId) + "\",";
  body += "\"event\":\"token_collected\",";
  body += "\"points\":" + String(points);
  body += "}";

  int statusCode = http.POST(body);
  String response = http.getString();

  Serial.println();
  Serial.println("========== RENDER FASTAPI ==========");
  Serial.print("POST: ");
  Serial.println(renderTokenCollectedUrl);
  Serial.print("Body: ");
  Serial.println(body);
  Serial.print("HTTP status: ");
  Serial.println(statusCode);
  Serial.print("Response: ");
  Serial.println(response);
  Serial.println("====================================");

  http.end();
  return statusCode >= 200 && statusCode < 300;
}

void readStepSensor() {
  if (millis() - lastSensorRead < sensorInterval) return;
  lastSensorRead = millis();

  sensors_event_t accel;
  sensors_event_t gyro;
  sensors_event_t temp;
  mpu.getEvent(&accel, &gyro, &temp);

  lastAx = accel.acceleration.x;
  lastAy = accel.acceleration.y;
  lastAz = accel.acceleration.z;

  float magnitudeG = sqrt(lastAx * lastAx + lastAy * lastAy + lastAz * lastAz) / 9.80665;
  float movement = abs(magnitudeG - lastMagnitudeG);
  lastMagnitudeG = magnitudeG;

  if (movement < 0.08) stepArmed = true;

  if (stepArmed && movement > stepThreshold && millis() - lastStepTime > minStepInterval) {
    steps++;
    pendingSteps++;
    lastStepTime = millis();
    stepArmed = false;

    logPrefix();
    Serial.print("Passo detectado. Total: ");
    Serial.println(steps);

    showTrackingScreen();
  }
}

void validateMissionAtTotem() {
  if (pendingSteps == 0) {
    setFeedback(false, true);
    beepError();
    showStatusScreen("Missao bloqueada", "Caminhe antes");
    publishFiwareTelemetry("no_steps", 0);
    delay(1500);
    showTrackingScreen();
    return;
  }

  validationCount++;
  int validatedSteps = pendingSteps;
  int eventPoints = validatedSteps * pointsPerStep;
  tokenValue = eventPoints;

  setFeedback(true, false);
  beepSuccess();
  showStatusScreen("Validando", "FIWARE + Render");

  publishFiwareTelemetry("validated", eventPoints);
  bool renderOk = notifyRenderTokenCollected(eventPoints);

  if (renderOk) {
    totalPoints += eventPoints;
    pendingSteps = 0;
    if (batteryLevel > 0) batteryLevel--;

    showStatusScreen("Missao validada", "App Render atualizado");
    publishFiwareTelemetry("render_synced", eventPoints);
  } else {
    setFeedback(false, true);
    beepError();
    showStatusScreen("Render pendente", "Inicie missao no app");
    publishFiwareTelemetry("render_error", eventPoints);
  }

  delay(2200);
  setFeedback(false, false);
  showTrackingScreen();
}

void setup() {
  Serial.begin(115200);

  pinMode(buttonPin, INPUT_PULLUP);
  pinMode(greenLedPin, OUTPUT);
  pinMode(redLedPin, OUTPUT);
  pinMode(buzzerPin, OUTPUT);
  setFeedback(false, false);

  Wire.begin(oledSdaPin, oledSclPin);
  mpuWire.begin(mpuSdaPin, mpuSclPin);

  if (!display.begin(SSD1306_SWITCHCAPVCC, 0x3C)) {
    Serial.println("Falha ao iniciar OLED.");
    while (true) delay(10);
  }

  showBootScreen("Iniciando");

  if (!mpu.begin(0x68, &mpuWire)) {
    Serial.println("Falha ao iniciar MPU6050.");
    showBootScreen("Erro MPU6050");
    while (true) delay(10);
  }

  mpu.setAccelerometerRange(MPU6050_RANGE_4_G);
  mpu.setGyroRange(MPU6050_RANGE_500_DEG);
  mpu.setFilterBandwidth(MPU6050_BAND_21_HZ);

  renderSecureClient.setInsecure();
  connectWiFi();

  mqttClient.setServer(mqttServer, mqttPort);
  mqttClient.setKeepAlive(60);
  mqttClient.setSocketTimeout(15);
  connectMQTT(true);

  showTrackingScreen();
  publishFiwareTelemetry(currentFlowState(), 0);
}

void loop() {
  if (WiFi.status() != WL_CONNECTED) {
    connectWiFi();
  }

  if (!mqttClient.connected()) {
    if (mqttWasConnected) {
      logInfo("MQTT desconectado. Tentando reconectar...");
      mqttWasConnected = false;
    }

    if (millis() - lastMqttReconnectAttempt > mqttReconnectInterval) {
      lastMqttReconnectAttempt = millis();
      connectMQTT(false);
    }
  } else {
    mqttClient.loop();
  }

  readStepSensor();

  if (mqttClient.connected() && millis() - lastTelemetryPublish > telemetryInterval) {
    lastTelemetryPublish = millis();
    publishFiwareTelemetry(currentFlowState(), 0);
  }

  if (digitalRead(buttonPin) == LOW && millis() - lastPressTime > debounceDelay) {
    lastPressTime = millis();
    logInfo("Botao pressionado. Validando missao.");
    validateMissionAtTotem();

    while (digitalRead(buttonPin) == LOW) {
      delay(10);
    }
  }
}
