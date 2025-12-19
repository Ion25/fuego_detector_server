/*
  Fire Detection System - Arduino MKR WiFi 1010 con MQTT
  Universidad Nacional de San Agustín - Arequipa, Perú
  
  Este código lee los sensores del MKR IoT Carrier y envía
  los datos al servidor backend vía MQTT (HiveMQ Cloud).
  
  ✅ Funciona con Arduino y Servidor en DIFERENTES REDES WiFi
  
  Sensores:
  - HTS221: Temperatura y Humedad
  - APDS9960: Luz ambiente
  - LPS22HB: Presión barométrica
*/

#include <WiFiNINA.h>
#include <ArduinoMqttClient.h>
#include <ArduinoJson.h>
#include <Arduino_MKRIoTCarrier.h>

// ============================================================================
// CONFIGURACIÓN WiFi - MODIFICA ESTOS VALORES
// ============================================================================
const char* ssid = "Redmi 9";           // Nombre de tu red WiFi (Arduino)
const char* password = "12345678";      // Contraseña de tu WiFi

// ============================================================================
// CONFIGURACIÓN MQTT - HiveMQ Cloud (Broker público)
// ============================================================================
const char* mqtt_broker = "broker.hivemq.com";
const int mqtt_port = 1883;
const char* mqtt_topic_sensores = "unsa/fire_detection/sensores";
const char* mqtt_topic_status = "unsa/fire_detection/status";
const char* mqtt_topic_comando = "unsa/fire_detection/comando";

// ============================================================================
// VARIABLES GLOBALES
// ============================================================================
MKRIoTCarrier carrier;
WiFiClient wifiClient;
MqttClient mqttClient(wifiClient);

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
  Serial.println("Fire Detection System - Arduino MQTT");
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
  carrier.display.setCursor(20, 90);
  carrier.display.print("Fire Detect");
  carrier.display.setCursor(40, 110);
  carrier.display.print("MQTT Mode");
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
    delay(1500);
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
  
  // Conectar a MQTT Broker
  Serial.println();
  Serial.print("Conectando a MQTT broker: ");
  Serial.println(mqtt_broker);
  
  if (!mqttClient.connect(mqtt_broker, mqtt_port)) {
    Serial.print("✗ Error de conexión MQTT. Código: ");
    Serial.println(mqttClient.connectError());
    
    carrier.display.fillScreen(0xF800);  // Rojo
    carrier.display.setTextColor(0xFFFF);
    carrier.display.setCursor(20, 110);
    carrier.display.print("MQTT Error!");
    while (1);  // Detener ejecución
  }
  
  Serial.println("✓ Conectado a MQTT broker!");
  Serial.print("   Topic sensores: ");
  Serial.println(mqtt_topic_sensores);
  
  // Suscribirse al topic de comandos
  mqttClient.subscribe(mqtt_topic_comando);
  Serial.print("✓ Suscrito a comandos: ");
  Serial.println(mqtt_topic_comando);
  
  // Publicar mensaje de inicio
  mqttClient.beginMessage(mqtt_topic_status);
  mqttClient.print("Arduino conectado - UNSA Fire Detection");
  mqttClient.endMessage();
  
  // Mostrar MQTT conectado en pantalla
  carrier.display.fillScreen(0x001F);  // Azul
  carrier.display.setTextColor(0xFFFF);
  carrier.display.setCursor(40, 100);
  carrier.display.print("MQTT OK!");
  carrier.display.setCursor(30, 130);
  carrier.display.setTextSize(1);
  carrier.display.print("Enviando datos...");
  delay(2000);
  
  Serial.println();
  Serial.println("✓ Sistema listo!");
  Serial.println("   Enviando datos cada 5 segundos vía MQTT...");
  Serial.println();
}

// ============================================================================
// LOOP PRINCIPAL
// ============================================================================
void loop() {
  // Mantener conexión MQTT
  mqttClient.poll();
  
  // Verificar si hay mensajes de comandos
  int messageSize = mqttClient.parseMessage();
  if (messageSize) {
    String topic = mqttClient.messageTopic();
    String message = "";
    
    while (mqttClient.available()) {
      message += (char)mqttClient.read();
    }
    
    Serial.print("📩 Comando recibido: ");
    Serial.println(message);
    
    // Procesar comando (puedes agregar más comandos aquí)
    if (message == "CAPTURA") {
      Serial.println("   Smartphone debe capturar imagen");
      // Activar alerta visual
      carrier.Buzzer.sound(800);
      delay(200);
      carrier.Buzzer.noSound();
    }
  }
  
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
    
    // Enviar datos vía MQTT
    enviarDatosMQTT(temperatura, luz, humedad, presion);
    
    Serial.println();
  }
  
  delay(100);  // Pequeña pausa
}

// ============================================================================
// FUNCIÓN: Enviar datos vía MQTT
// ============================================================================
void enviarDatosMQTT(float temp, float luz, float hum, float pres) {
  // Verificar conexión WiFi
  if (WiFi.status() != WL_CONNECTED) {
    Serial.println("✗ WiFi desconectado. Intentando reconectar...");
    WiFi.begin(ssid, password);
    delay(2000);
    
    if (WiFi.status() != WL_CONNECTED) {
      Serial.println("✗ No se pudo reconectar al WiFi");
      return;
    }
  }
  
  // Verificar conexión MQTT
  if (!mqttClient.connected()) {
    Serial.println("✗ MQTT desconectado. Intentando reconectar...");
    
    if (!mqttClient.connect(mqtt_broker, mqtt_port)) {
      Serial.print("✗ Error de reconexión MQTT. Código: ");
      Serial.println(mqttClient.connectError());
      return;
    }
    
    // Re-suscribirse a comandos
    mqttClient.subscribe(mqtt_topic_comando);
    Serial.println("✓ Reconectado a MQTT");
  }
  
  // Crear JSON con los datos
  StaticJsonDocument<200> doc;
  doc["temperatura"] = temp;
  doc["luz"] = luz;
  doc["humedad"] = hum;
  doc["presion"] = pres;
  
  String jsonString;
  serializeJson(doc, jsonString);
  
  Serial.print("📡 Enviando vía MQTT... ");
  
  // Publicar en MQTT
  mqttClient.beginMessage(mqtt_topic_sensores);
  mqttClient.print(jsonString);
  int result = mqttClient.endMessage();
  
  if (result) {
    Serial.println("✓ Mensaje publicado");
    
    // Indicador visual de envío exitoso
    carrier.display.fillRect(200, 10, 30, 30, 0x07E0);  // Verde
  } else {
    Serial.println("✗ Error al publicar mensaje");
    
    // Indicador visual de error
    carrier.display.fillRect(200, 10, 30, 30, 0xF800);  // Rojo
  }
}
