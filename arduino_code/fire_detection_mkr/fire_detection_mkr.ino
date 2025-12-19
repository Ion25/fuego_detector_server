/*
  Fire Detection System - Arduino MKR WiFi 1010
  Universidad Nacional de San Agustín - Arequipa, Perú
  
  Este código lee los sensores del MKR IoT Carrier y envía
  los datos al servidor backend cada 5 segundos.
  
  Sensores:
  - HTS221: Temperatura y Humedad
  - APDS9960: Luz ambiente
  - LPS22HB: Presión barométrica
*/

#include <WiFiNINA.h>
#include <ArduinoHttpClient.h>
#include <ArduinoJson.h>
#include <Arduino_MKRIoTCarrier.h>

// ============================================================================
// CONFIGURACIÓN WiFi - MODIFICA ESTOS VALORES
// ============================================================================
const char* ssid = "Redmi 9";           // Nombre de tu red WiFi
const char* password = "12345678";   // Contraseña de tu WiFi

// ============================================================================
// CONFIGURACIÓN DEL SERVIDOR - MODIFICA LA IP DE TU LAPTOP
// ============================================================================
const char* serverIP = "10.23.127.39";      // IP de tu laptop
const int serverPort = 5000;
const char* serverPath = "/api/sensores";

// ============================================================================
// VARIABLES GLOBALES
// ============================================================================
MKRIoTCarrier carrier;
WiFiClient wifiClient;
HttpClient httpClient = HttpClient(wifiClient, serverIP, serverPort);

unsigned long lastSendTime = 0;
const unsigned long sendInterval = 5000;  // Enviar cada 5 segundos

// ============================================================================
// SETUP - Inicialización
// ============================================================================
void setup() {
  // Iniciar comunicación serial
  Serial.begin(9600);
  while (!Serial && millis() < 5000);  // Esperar 5 segundos máximo
  
  Serial.println("========================================");
  Serial.println("Fire Detection System - Arduino");
  Serial.println("UNSA - Arequipa, Peru");
  Serial.println("========================================");
  Serial.println();
  
  // Inicializar MKR IoT Carrier
  Serial.println("Inicializando MKR IoT Carrier...");
  if (!carrier.begin()) {
    Serial.println("ERROR: No se pudo inicializar el Carrier!");
    Serial.println("Verifica que el MKR WiFi 1010 esté en el Carrier");
    while (1);  // Detener ejecución
  }
  Serial.println("✓ Carrier inicializado");
  
  // Mostrar mensaje en pantalla
  carrier.display.fillScreen(0x0000);  // Negro
  carrier.display.setTextColor(0xFFFF); // Blanco
  carrier.display.setTextSize(2);
  carrier.display.setCursor(20, 100);
  carrier.display.print("Fire Detection");
  carrier.display.setCursor(60, 130);
  carrier.display.print("UNSA");
  
  // Conectar a WiFi
  Serial.println();
  Serial.print("Conectando a WiFi: ");
  Serial.println(ssid);
  
  int attempts = 0;
  while (WiFi.status() != WL_CONNECTED && attempts < 20) {
    WiFi.begin(ssid, password);
    delay(500);
    Serial.print(".");
    attempts++;
  }
  
  if (WiFi.status() == WL_CONNECTED) {
    Serial.println();
    Serial.println("✓ WiFi conectado!");
    Serial.print("   IP: ");
    Serial.println(WiFi.localIP());
    Serial.print("   RSSI: ");
    Serial.print(WiFi.RSSI());
    Serial.println(" dBm");
    
    // Mostrar WiFi conectado en pantalla
    carrier.display.fillScreen(0x07E0);  // Verde
    carrier.display.setTextColor(0x0000);
    carrier.display.setCursor(40, 110);
    carrier.display.print("WiFi OK!");
    delay(2000);
  } else {
    Serial.println();
    Serial.println("✗ Error al conectar WiFi");
    Serial.println("  Verifica SSID y contraseña");
    
    // Mostrar error en pantalla
    carrier.display.fillScreen(0xF800);  // Rojo
    carrier.display.setTextColor(0xFFFF);
    carrier.display.setCursor(20, 110);
    carrier.display.print("WiFi Error!");
    while (1);  // Detener ejecución
  }
  
  Serial.println();
  Serial.println("✓ Sistema listo!");
  Serial.println("   Enviando datos cada 5 segundos...");
  Serial.println();
}

// ============================================================================
// LOOP PRINCIPAL
// ============================================================================
void loop() {
  // Verificar si es momento de enviar datos
  if (millis() - lastSendTime >= sendInterval) {
    lastSendTime = millis();
    
    // Leer sensores
    float temperatura = carrier.Env.readTemperature();
    float humedad = carrier.Env.readHumidity();
    float presion = carrier.Pressure.readPressure();
    
    // Leer luz (APDS9960)
    int r, g, b;
    while (!carrier.Light.colorAvailable()) {
      delay(5);
    }
    carrier.Light.readColor(r, g, b);
    
    // Calcular luz promedio (lux aproximado)
    float luz = (r + g + b) / 3.0;
    
    // Mostrar en Serial Monitor
    Serial.println("─────────────────────────────────");
    Serial.print("🌡️  Temperatura: ");
    Serial.print(temperatura, 1);
    Serial.println(" °C");
    
    Serial.print("💧 Humedad: ");
    Serial.print(humedad, 1);
    Serial.println(" %");
    
    Serial.print("🌀 Presión: ");
    Serial.print(presion, 2);
    Serial.println(" kPa");
    
    Serial.print("💡 Luz: ");
    Serial.print(luz, 0);
    Serial.println(" (RGB avg)");
    
    // Mostrar en pantalla del Carrier
    carrier.display.fillScreen(0x0000);
    carrier.display.setTextColor(0xFFFF);
    carrier.display.setTextSize(2);
    
    carrier.display.setCursor(10, 40);
    carrier.display.print("Temp: ");
    carrier.display.print(temperatura, 1);
    carrier.display.print("C");
    
    carrier.display.setCursor(10, 70);
    carrier.display.print("Luz: ");
    carrier.display.print(luz, 0);
    
    carrier.display.setCursor(10, 100);
    carrier.display.print("Hum: ");
    carrier.display.print(humedad, 1);
    carrier.display.print("%");
    
    carrier.display.setCursor(10, 130);
    carrier.display.print("Pres: ");
    carrier.display.print(presion, 1);
    
    // Enviar datos al servidor
    enviarDatosServidor(temperatura, luz, humedad, presion);
    
    Serial.println();
  }
  
  delay(100);  // Pequeña pausa
}

// ============================================================================
// FUNCIÓN: Enviar datos al servidor
// ============================================================================
void enviarDatosServidor(float temp, float luz, float hum, float pres) {
  // Verificar conexión WiFi
  if (WiFi.status() != WL_CONNECTED) {
    Serial.println("✗ WiFi desconectado. Intentando reconectar...");
    WiFi.begin(ssid, password);
    delay(2000);
    
    if (WiFi.status() != WL_CONNECTED) {
      Serial.println("✗ No se pudo reconectar");
      return;
    }
  }
  
  // Crear JSON con los datos
  StaticJsonDocument<200> doc;
  doc["temperatura"] = temp;
  doc["luz"] = luz;
  doc["humedad"] = hum;
  doc["presion"] = pres;
  
  String jsonString;
  serializeJson(doc, jsonString);
  
  Serial.print("📡 Enviando al servidor... ");
  
  // Hacer POST request
  httpClient.beginRequest();
  httpClient.post(serverPath);
  httpClient.sendHeader("Content-Type", "application/json");
  httpClient.sendHeader("Content-Length", jsonString.length());
  httpClient.beginBody();
  httpClient.print(jsonString);
  httpClient.endRequest();
  
  // Leer respuesta
  int statusCode = httpClient.responseStatusCode();
  String response = httpClient.responseBody();
  
  if (statusCode == 200) {
    Serial.print("✓ OK (");
    Serial.print(statusCode);
    Serial.println(")");
    
    // Parsear respuesta
    StaticJsonDocument<200> responseDoc;
    deserializeJson(responseDoc, response);
    
    const char* estado = responseDoc["estado"];
    Serial.print("   Estado del sistema: ");
    Serial.println(estado);
    
    // Cambiar color de pantalla según estado
    if (strcmp(estado, "Normal") == 0) {
      // Verde - Todo normal
      carrier.display.fillRect(200, 10, 30, 30, 0x07E0);
    } else if (strcmp(estado, "Alerta") == 0) {
      // Amarillo - Alerta
      carrier.display.fillRect(200, 10, 30, 30, 0xFFE0);
    } else if (strcmp(estado, "Peligro") == 0) {
      // Rojo - Peligro
      carrier.display.fillRect(200, 10, 30, 30, 0xF800);
      
      // Activar buzzer como alerta
      carrier.Buzzer.sound(1000);  // 1000 Hz
      delay(200);
      carrier.Buzzer.noSound();
    }
    
  } else {
    Serial.print("✗ Error (");
    Serial.print(statusCode);
    Serial.println(")");
    Serial.print("   Respuesta: ");
    Serial.println(response);
  }
}
