# 🔥 Sistema IoT de Detección de Incendios

Sistema completo de detección temprana de incendios utilizando tecnologías IoT, análisis de imágenes con visión artificial y notificaciones en tiempo real.

![Estado del Proyecto](https://img.shields.io/badge/estado-activo-success.svg)
![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)
![FastAPI](https://img.shields.io/badge/FastAPI-0.104+-green.svg)
![Arduino](https://img.shields.io/badge/Arduino-1.8+-teal.svg)
![Licencia](https://img.shields.io/badge/licencia-MIT-blue.svg)

## 📋 Descripción

Este proyecto implementa un sistema completo de detección de incendios que integra:

- **Nodo sensor Arduino** con sensores de temperatura (DHT22), luz (LDR), humedad y presión (BMP180)
- **Servidor backend** en Python con FastAPI para procesamiento en tiempo real
- **Cámara inteligente** basada en Android para captura y análisis de imágenes
- **Dashboard web** con visualización en tiempo real de datos y eventos
- **Notificaciones automáticas** vía Telegram Bot
- **Análisis de imágenes** mediante heurística HSV (preparado para modelos de Deep Learning)

### 🎯 Funcionamiento

1. Arduino monitorea continuamente temperatura, luz, humedad y presión
2. El servidor evalúa umbrales de riesgo (Normal → Alerta → Peligro)
3. Al detectar estado de Peligro, solicita automáticamente 5 fotos a la cámara Android
4. Las imágenes se analizan con algoritmos de visión artificial para confirmar presencia de fuego
5. Si se confirma el incendio, se envía notificación inmediata por Telegram con evidencia fotográfica

## 🏗️ Arquitectura del Sistema

```
┌─────────────┐      MQTT/HTTP      ┌──────────────────┐
│   Arduino   │ ───────────────────> │  Servidor FastAPI│
│  + Sensores │                      │   + SQLite DB    │
└─────────────┘                      └────────┬─────────┘
                                              │
                    ┌─────────────────────────┼─────────────────────┐
                    │                         │                     │
                    ▼                         ▼                     ▼
            ┌──────────────┐          ┌─────────────┐      ┌──────────────┐
            │   Cámara     │          │  Dashboard  │      │  Telegram    │
            │   Android    │          │     Web     │      │     Bot      │
            │  (Termux)    │          │  (Chart.js) │      │              │
            └──────────────┘          └─────────────┘      └──────────────┘
```

## 🚀 Características

- ✅ **Detección temprana multi-sensor**: Temperatura, luz, humedad y presión
- ✅ **Confirmación visual automática**: Captura y análisis de 5 fotografías secuenciales
- ✅ **Notificaciones en tiempo real**: Alertas inmediatas vía Telegram
- ✅ **Dashboard web responsivo**: Monitoreo en tiempo real con gráficos históricos
- ✅ **Base de datos SQLite**: Registro completo de eventos y análisis
- ✅ **Comunicación MQTT**: Arquitectura pub/sub escalable y eficiente
- ✅ **API REST documentada**: Endpoints para integración con otros sistemas
- ✅ **Análisis heurístico HSV**: Detección de fuego por patrones de color
- 🔄 **Preparado para IA**: Estructura lista para integrar modelos TensorFlow Lite

## 📦 Requisitos

### Hardware

- **Arduino Uno** (o compatible)
- **DHT22**: Sensor de temperatura y humedad
- **LDR**: Fotoresistencia (sensor de luz)
- **BMP180**: Sensor de presión barométrica
- **Smartphone Android** (8.0+) con cámara funcional
- **Servidor**: Raspberry Pi, PC Linux/Windows o servidor en la nube

### Software

- **Python 3.8** o superior
- **Arduino IDE 2.x**
- **Android** con Termux instalado
- Cuenta de **Telegram**

## 🔧 Instalación Paso a Paso

### 1. Clonar el Repositorio

\`\`\`bash
git clone https://github.com/Ion25/fuego_detector_server.git
cd fuego_detector_server
\`\`\`

### 2. Configurar Servidor Backend

\`\`\`bash
# Crear entorno virtual
python3 -m venv venv

# Activar entorno virtual
source venv/bin/activate  # En Linux/Mac
# venv\Scripts\activate   # En Windows

# Instalar dependencias
pip install -r requirements.txt

# Crear directorios necesarios
mkdir -p uploads/images uploads/audio logs
\`\`\`

### 3. Configurar Telegram Bot

1. Abre Telegram y busca **@BotFather**
2. Envía \`/newbot\` y sigue las instrucciones
3. Copia el **token** proporcionado
4. Obtén tu **Chat ID** usando @userinfobot
5. Crea el archivo de configuración:

\`\`\`bash
cp telegram_config.py.example telegram_config.py
\`\`\`

Edita \`telegram_config.py\` con tus credenciales:

\`\`\`python
BOT_TOKEN = "tu_token_de_botfather_aqui"
CHAT_ID = "tu_chat_id_aqui"
\`\`\`

### 4. Programar Arduino

1. Abre **Arduino IDE**
2. Instala las librerías necesarias desde el Library Manager:
   - **DHT sensor library** (by Adafruit)
   - **Adafruit BMP085 Library**
3. Abre el sketch: \`arduino_code/fire_detection_mkr_mqtt/fire_detection_mkr_mqtt.ino\`
4. Ajusta los pines según tu conexión física:
   - DHT22 → Pin Digital 2
   - LDR → Pin Analógico A0
   - BMP180 → I2C (SDA: A4, SCL: A5)
5. Si usas WiFi shield, configura tu red en el código
6. Sube el sketch a tu Arduino

### 5. Configurar Cámara Android (Termux)

En tu dispositivo Android:

\`\`\`bash
# 1. Instalar Termux desde F-Droid (NO desde Play Store)
# https://f-droid.org/en/packages/com.termux/

# 2. Instalar Termux:API también desde F-Droid
# https://f-droid.org/en/packages/com.termux.api/

# 3. Dentro de Termux, ejecutar:
pkg update && pkg upgrade
pkg install python python-pip termux-api

# 4. Instalar dependencias Python
pip install paho-mqtt requests

# 5. Copiar el script al dispositivo
# Transferir camera_mqtt_android.py usando cable USB, email o Termux desde PC

# 6. Dar permisos de cámara a Termux:
termux-camera-photo test.jpg

# 7. Ejecutar el script
python camera_mqtt_android.py
\`\`\`

**Importante**: El dispositivo Android debe permanecer con Termux abierto. Usa Termux:Wake Lock para evitar suspensión.

### 6. Iniciar el Sistema

\`\`\`bash
# En el servidor, iniciar FastAPI
python server.py

# El servidor se iniciará en:
# http://localhost:8000

# Acceder al dashboard:
# http://localhost:8000/dashboard
\`\`\`

## 🎮 Uso del Sistema

### Acceder al Dashboard

Abre tu navegador y ve a: **http://localhost:8000/dashboard**

El dashboard muestra:

- **Indicador de estado** con código de colores (Verde/Amarillo/Naranja/Rojo)
- **Lecturas en tiempo real** de los 4 sensores
- **Gráficos históricos** con Chart.js
- **Galería de imágenes** de las últimas 5 capturas
- **Log de eventos** cronológico del sistema

### Umbrales de Detección

| Estado | Condición |
|--------|-----------|
| **Normal** | Temperatura < 45°C y Luz < 800 lux |
| **Alerta** | Temperatura ≥ 45°C o Luz ≥ 800 lux |
| **Peligro** | Temperatura ≥ 55°C o Luz ≥ 1000 lux |
| **Fuego Confirmado** | Peligro + ≥3% píxeles de fuego en imágenes |

Puedes modificar los umbrales en \`server.py\`:

\`\`\`python
UMBRALES = {
    "temp_alerta": 45.0,
    "temp_peligro": 55.0,
    "luz_alerta": 800,
    "luz_peligro": 1000
}
\`\`\`

## 📡 API REST

### Endpoints Principales

| Método | Endpoint | Descripción |
|--------|----------|-------------|
| \`GET\` | \`/api/estado\` | Estado global del sistema |
| \`POST\` | \`/api/sensores\` | Recibir datos de Arduino |
| \`POST\` | \`/api/upload\` | Subir imagen desde cámara |
| \`GET\` | \`/api/eventos\` | Log de eventos |
| \`GET\` | \`/api/historico\` | Histórico de lecturas |
| \`GET\` | \`/api/ultimas-fotos\` | URLs de capturas |
| \`GET\` | \`/dashboard\` | Interfaz web |
| \`GET\` | \`/docs\` | Documentación Swagger |

### Ejemplo de Uso

\`\`\`bash
# Enviar datos de sensores
curl -X POST http://localhost:8000/api/sensores \\
  -H "Content-Type: application/json" \\
  -d '{"temperatura": 48.5, "luz": 850, "humedad": 35.2, "presion": 1013.25}'

# Obtener estado actual
curl http://localhost:8000/api/estado
\`\`\`

## 🧪 Pruebas sin Hardware

Si no tienes el hardware físico:

\`\`\`bash
# Simular Arduino enviando datos aleatorios
python simulate_arduino.py

# Simular condición de peligro inmediata
python test_simulate_danger.py
\`\`\`

## 📊 Base de Datos

SQLite con 3 tablas:

- **lecturas_sensores**: Histórico de datos de sensores
- **eventos**: Log de alertas y confirmaciones
- **analisis_ia**: Resultados de análisis de imágenes

Consultar manualmente:

\`\`\`bash
sqlite3 fire_detection.db
sqlite> SELECT * FROM eventos ORDER BY timestamp DESC LIMIT 5;
\`\`\`

## 🔒 Seguridad

- ⚠️ **NUNCA subas** \`telegram_config.py\` con credenciales reales a GitHub
- El \`.gitignore\` excluye automáticamente archivos sensibles
- En producción, usa variables de entorno:

\`\`\`bash
export TELEGRAM_BOT_TOKEN="tu_token"
export TELEGRAM_CHAT_ID="tu_chat_id"
\`\`\`

## 📁 Estructura del Proyecto

\`\`\`
fuego_detector_server/
├── server.py                    # ⚡ Servidor FastAPI principal
├── mqtt_config.py               # 📡 Cliente MQTT
├── telegram_config.py.example   # 📱 Plantilla Telegram
├── camera_mqtt_android.py       # 📷 Script cámara Android
├── requirements.txt             # 📦 Dependencias
├── arduino_code/                # 🤖 Código Arduino
│   └── fire_detection_mkr_mqtt/ 
├── models/                      # 🧠 Análisis IA
│   └── script-IA.py
├── templates/                   # 🎨 HTML Templates
│   └── dashboard.html
└── uploads/                     # 📸 Imágenes capturadas (no en Git)
\`\`\`

## 🚧 Mejoras Futuras

- [ ] Modelo de Deep Learning (MobileNetV2/YOLOv8) para >90% precisión
- [ ] Detección de humo con sensor MQ-2
- [ ] Red mesh de múltiples nodos
- [ ] App móvil nativa con push notifications
- [ ] Integración con sistemas de extinción
- [ ] Análisis predictivo con ML

## 🤝 Contribuir

¡Las contribuciones son bienvenidas!

1. Lee [CONTRIBUTING.md](CONTRIBUTING.md)
2. Fork el proyecto
3. Crea tu feature branch (\`git checkout -b feature/AmazingFeature\`)
4. Commit tus cambios (\`git commit -m 'Add: nueva funcionalidad'\`)
5. Push a la rama (\`git push origin feature/AmazingFeature\`)
6. Abre un Pull Request

## ❓ FAQ

**P: ¿Funciona sin cámara?**  
R: Sí, detecta con sensores, pero la cámara mejora la precisión significativamente.

**P: ¿Puedo usar ESP32?**  
R: Sí, compatible. ESP32 tiene WiFi integrado, ventaja sobre Arduino Uno.

**P: ¿Cómo despliego en producción?**  
R: Usa Heroku, Railway.app, o VPS con systemd/supervisor para mantener servidor activo 24/7.

## 📝 Licencia

MIT License - Ver [LICENSE](LICENSE)

## 👥 Autores

**Universidad Nacional de San Agustín de Arequipa**  
Facultad de Ingeniería de Producción y Servicios  
Escuela Profesional de Ingeniería Electrónica

## 🙏 Agradecimientos

- Comunidad Arduino y FastAPI
- D-Fire Dataset para entrenamiento de modelos
- HiveMQ por broker MQTT gratuito
- Chart.js por visualizaciones
- Termux por Python en Android

---

⭐ **Si este proyecto te fue útil, dale una estrella en GitHub!**

**Desarrollado con ❤️ para seguridad contra incendios**
