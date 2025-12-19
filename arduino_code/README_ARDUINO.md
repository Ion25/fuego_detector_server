# 🔥 Código Arduino - Fire Detection System

## 📋 Información del Hardware

**Placa detectada:** Arduino MKR WiFi 1010  
**Puerto:** `/dev/ttyACM0`  
**FQBN:** `arduino:samd:mkrwifi1010`

## ✅ Estado de Compilación

```
✓ Compilación exitosa
✓ Uso de memoria: 45% (119,132 bytes / 262,144 bytes)
✓ Variables globales: 23% (7,732 bytes / 32,768 bytes)
✓ Todas las librerías instaladas
```

## 📝 Antes de Subir el Código

### 1. Configurar WiFi

Edita el archivo `fire_detection_mkr.ino` y modifica estas líneas:

```cpp
const char* ssid = "TU_RED_WIFI";           // ← Nombre de tu WiFi
const char* password = "TU_PASSWORD_WIFI";   // ← Contraseña
```

### 2. Configurar IP del Servidor

Necesitas la IP de tu laptop. Para obtenerla:

```bash
ip addr show | grep "inet " | grep -v 127.0.0.1
```

Luego modifica esta línea en el código:

```cpp
const char* serverIP = "192.168.1.100";  // ← IP de tu laptop
```

## 🚀 Cómo Subir el Código

### Opción 1: Con Arduino CLI (Recomendado)

```bash
# Desde la carpeta del proyecto
cd arduino_code/fire_detection_mkr

# Compilar
arduino-cli compile --fqbn arduino:samd:mkrwifi1010 .

# Subir al Arduino
arduino-cli upload -p /dev/ttyACM0 --fqbn arduino:samd:mkrwifi1010 .
```

### Opción 2: Comando único (compilar y subir)

```bash
cd arduino_code/fire_detection_mkr
arduino-cli compile --upload -p /dev/ttyACM0 --fqbn arduino:samd:mkrwifi1010 .
```

## 👀 Monitorear Salida Serial

Para ver los mensajes del Arduino en tiempo real:

```bash
arduino-cli monitor -p /dev/ttyACM0 -c baudrate=9600
```

O con `screen`:

```bash
screen /dev/ttyACM0 9600
# Para salir: Ctrl+A luego K
```

## 📊 Qué Hace el Código

1. **Inicialización:**
   - Conecta al WiFi configurado
   - Inicializa todos los sensores del MKR IoT Carrier
   - Muestra mensajes en la pantalla del Carrier

2. **Loop principal (cada 5 segundos):**
   - Lee temperatura, humedad, presión y luz
   - Muestra valores en Serial Monitor y pantalla
   - Envía datos al servidor vía HTTP POST
   - Recibe respuesta del servidor con el estado del sistema

3. **Indicadores visuales:**
   - 🟢 Verde: Estado Normal
   - 🟡 Amarillo: Estado Alerta
   - 🔴 Rojo: Estado Peligro (+ sonido de buzzer)

## 🔧 Solución de Problemas

### Error: "Permission denied" en /dev/ttyACM0

```bash
# Agregar tu usuario al grupo dialout
sudo usermod -a -G dialout $USER

# Cerrar sesión y volver a entrar
# O ejecutar:
newgrp dialout
```

### No se puede conectar a WiFi

1. Verifica que el SSID y password estén correctos
2. Verifica que tu red WiFi sea 2.4GHz (el MKR WiFi 1010 no soporta 5GHz)
3. Acércate al router WiFi

### El Arduino se resetea al abrir el monitor serial

Esto es normal en las placas SAMD. Espera unos segundos después de abrir el monitor.

### Error al subir código

1. Verifica que el Arduino esté conectado: `arduino-cli board list`
2. Asegúrate de que no haya otro programa usando el puerto (cierra Arduino IDE si está abierto)
3. Intenta presionar el botón RESET del Arduino 2 veces rápidamente para entrar en modo bootloader

## 📡 Endpoints del Servidor

El Arduino envía datos a:

```
POST http://<IP_SERVIDOR>:5000/api/sensores

Payload:
{
  "temperatura": 28.5,
  "luz": 450.0,
  "humedad": 60.0,
  "presion": 1013.25
}

Respuesta:
{
  "status": "ok",
  "estado": "Normal",
  "timestamp": "2025-12-12T..."
}
```

## 📋 Librerías Instaladas

- ✅ Arduino_MKRIoTCarrier (2.1.0)
- ✅ WiFiNINA (1.9.1)
- ✅ ArduinoHttpClient (0.6.1)
- ✅ ArduinoJson (7.4.2)
- ✅ Arduino_HTS221 (Temperatura/Humedad)
- ✅ Arduino_LPS22HB (Presión)
- ✅ Arduino_APDS9960 (Luz/Color)
- ✅ Arduino_LSM6DS3 (Acelerómetro)

## 🎯 Próximos Pasos

1. ✏️  Editar configuración WiFi e IP del servidor
2. 🔄 Compilar el código
3. ⬆️  Subir al Arduino
4. 📊 Monitorear salida serial
5. 👀 Ver dashboard del servidor: http://localhost:5000/dashboard

---

**Fecha:** 12 de Diciembre 2025  
**Universidad:** UNSA - Arequipa, Perú  
**Proyecto:** Sistema IoT de Detección de Incendios
