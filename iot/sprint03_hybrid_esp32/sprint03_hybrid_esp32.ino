#include <HTTPClient.h>
#include <WiFi.h>
#include <WiFiClientSecure.h>

// CarePlus Sprint 03 - Totem ESP32
// O app no celular conta passos, le a tag NFC e valida a missao no Render.
// O ESP32 apenas consulta o status do totem e mostra feedback fisico.

const char* ssid = "Wokwi-GUEST";
const char* password = "";

const char* backendUrl =
  "https://careplus-sprint3-umkto.onrender.com/iot/totem-status/totem001";

const int ledSuccess = 18;
const int ledError = 19;
const int buzzer = 23;

const unsigned long pollInterval = 1500;

String lastStatus = "";
unsigned long lastPoll = 0;
WiFiClientSecure secureClient;

void setFeedbackLights(bool successOn, bool errorOn) {
  digitalWrite(ledSuccess, successOn ? HIGH : LOW);
  digitalWrite(ledError, errorOn ? HIGH : LOW);
}

void beepSuccess() {
  tone(buzzer, 1200, 160);
  delay(200);
  tone(buzzer, 1600, 180);
}

void beepError() {
  tone(buzzer, 300, 450);
}

void beepValidating() {
  tone(buzzer, 900, 80);
}

void applyStatus(const String& status) {
  if (status == "success") {
    setFeedbackLights(true, false);
    beepSuccess();
    return;
  }

  if (status == "error") {
    setFeedbackLights(false, true);
    beepError();
    return;
  }

  if (status == "validating") {
    setFeedbackLights(true, true);
    beepValidating();
    return;
  }

  setFeedbackLights(false, false);
}

String parseStatus(String payload) {
  payload.replace(" ", "");
  payload.replace("\n", "");
  payload.replace("\r", "");
  payload.replace("\t", "");

  if (payload.indexOf("\"status\":\"success\"") >= 0) return "success";
  if (payload.indexOf("\"status\":\"error\"") >= 0) return "error";
  if (payload.indexOf("\"status\":\"validating\"") >= 0) return "validating";
  return "idle";
}

void connectWiFi() {
  WiFi.mode(WIFI_STA);
  WiFi.begin(ssid, password);
  Serial.print("Conectando ao Wi-Fi");

  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }

  Serial.println();
  Serial.print("Wi-Fi conectado. IP: ");
  Serial.println(WiFi.localIP());
}

void readTotemStatus() {
  HTTPClient http;
  http.begin(secureClient, backendUrl);

  int statusCode = http.GET();

  Serial.print("HTTP status: ");
  Serial.println(statusCode);

  if (statusCode == 200) {
    String payload = http.getString();
    String status = parseStatus(payload);

    Serial.print("Payload: ");
    Serial.println(payload);

    if (status != lastStatus) {
      Serial.print("Status do totem: ");
      Serial.println(status);
      applyStatus(status);
      lastStatus = status;
    }
  } else {
    Serial.print("Falha HTTP: ");
    Serial.println(statusCode);
    applyStatus("error");
    lastStatus = "http_error";
  }

  http.end();
}

void setup() {
  Serial.begin(115200);

  pinMode(ledSuccess, OUTPUT);
  pinMode(ledError, OUTPUT);
  pinMode(buzzer, OUTPUT);
  setFeedbackLights(false, false);

  secureClient.setInsecure();
  connectWiFi();

  Serial.print("Consultando backend: ");
  Serial.println(backendUrl);
}

void loop() {
  if (WiFi.status() != WL_CONNECTED) {
    setFeedbackLights(false, true);
    connectWiFi();
    delay(1000);
    return;
  }

  if (millis() - lastPoll >= pollInterval) {
    lastPoll = millis();
    readTotemStatus();
  }
}
