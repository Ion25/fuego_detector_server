# Sistema IoT de Detección de Incendios

Sistema completo de detección temprana de incendios utilizando tecnologías IoT, análisis de imágenes con visión artificial y notificaciones en tiempo real.

![Estado del Proyecto](https://img.shields.io/badge/estado-activo-success.svg)
![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)
![FastAPI](https://img.shields.io/badge/FastAPI-0.104+-green.svg)
![Arduino](https://img.shields.io/badge/Arduino-1.8+-teal.svg)
![Licencia](https://img.shields.io/badge/licencia-MIT-blue.svg)

## Descripción

Este proyecto implementa un sistema completo de detección de incendios que integra:

- **Nodo sensor Arduino** con sensores de temperatura (DHT22), luz (LDR), humedad y presión (BMP180)
- **Servidor backend** en Python con FastAPI para procesamiento en tiempo real
- **Cámara inteligente** basada en Android para captura y análisis de imágenes
- **Dashboard web** con visualización en tiempo real de datos y eventos
- **Notificaciones automáticas** vía Telegram Bot
- **Análisis de imágenes** mediante heurística HSV (preparado para modelos de Deep Learning)

### Funcionamiento

1. Arduino monitorea continuamente temperatura, luz, humedad y presión
2. El servidor evalúa umbrales de riesgo (Normal → Alerta → Peligro)
3. Al detectar estado de Peligro, solicita automáticamente 5 fotos a la cámara Android
4. Las imágenes se analizan con algoritmos de visión artificial para confirmar presencia de fuego
5. Si se confirma el incendio, se envía notificación inmediata por Telegram con evidencia fotográfica

## Arquitectura del Sistema

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

## Características

- **Detección temprana multi-sensor**: Temperatura, luz, humedad y presión
- **Confirmación visual automática**: Captura y análisis de 5 fotografías secuenciales
- **Notificaciones en tiempo real**: Alertas inmediatas vía Telegram
- **Dashboard web responsivo**: Monitoreo en tiempo real con gráficos históricos
- **Base de datos SQLite**: Registro completo de eventos y análisis
- **Comunicación MQTT**: Arquitectura pub/sub escalable y eficiente
- **API REST**: Endpoints documentados para integración con otros sistemas
- **Análisis heurístico HSV**: Detección de fuego por patrones de color
- **Preparado para IA**: Estructura lista para integrar modelos TensorFlow Lite

## Requisitos

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

## Instalación

### 1. Clonar el Repositorio

```bash
git clone https://github.com/Ion25/fuego_detector_server.git
cd fuego_detector_server
```

### 2. Configurar Servidor Backend

```bash
# Crear entorno virtual
python3 -m venv venv
source venv/bin/activate  # En Linux/Mac
# venv\Scripts\activate   # En Windows

# Instalar dependencias
pip install -r requirements.txt

# Crear directorios necesarios
mkdir -p uploads/images uploads/audio logs
```

### 3. Configurar Telegram Bot

1. Abre Telegram y busca **@BotFather**
2. Envía `/newbot` y sigue las instrucciones
3. Copia el **token** proporcionado
4. Obtén tu **Chat ID** usando @userinfobot
5. Crea el archivo de configuración:

```bash
cp telegram_config.py.example telegram_config.py
```

Edita `telegram_config.py` con tus credenciales:

```python
BOT_TOKEN = "tu_token_aqui"
CHAT_ID = "tu_chat_id_aqui"
```

### 4. Programar Arduino

1. Abre Arduino IDE
2. Instala las librerías necesarias:
   - **DHT sensor library** (Adafruit)
   - **Adafruit BMP085 Library**
3. Abre el sketch: `arduino_code/fire_detection_mkr_mqtt/fire_detection_mkr_mqtt.ino`
4. Ajusta los pines según tu conexión:
   - DHT22 → Pin Digital 2
   - LDR → Pin Analógico A0
   - BMP180 → I2C (SDA: A4, SCL: A5)
5. **Configura tu WiFi** en el código (si usas WiFi shield)
6. Sube el sketch a tu Arduino

### 5. Configurar Cámara Android (Termux)

En tu dispositivo Android:

```bash
# 1. Instalar Termux desde F-Droid o GitHub
# https://f-droid.org/en/packages/com.termux/

# 2. Dentro de Termux, ejecutar:
pkg update && pkg upgrade
pkg install python python-pip termux-api

# 3. Instalar Termux:API desde F-Droid también
# https://f-droid.org/en/packages/com.termux.api/

# 4. Instalar dependencias Python
pip install paho-mqtt requests

# 5. Copiar el script de cámara al dispositivo
# Transferir camera_mqtt_android.py usando USB, email o cloud

# 6. Ejecutar el script
python camera_mqtt_android.py
```

**Nota**: El dispositivo Android debe permanecer con pantalla encendida o usar Termux:Wake Lock.

### 6. Iniciar el Sistema

```bash
# Terminal 1: Iniciar servidor
python server.py

# El servidor se iniciará en:
# http://localhost:8000

# El dashboard estará disponible en:
# http://localhost:8000/dashboard
```

## Uso

### Dashboard Web

Accede a `http://localhost:8000/dashboard` para ver:

- **Estado del sistema** en tiempo real (Normal/Alerta/Peligro/Fuego Confirmado)
- **Lecturas de sensores** actualizadas cada 2 segundos
- **Gráficos históricos** de los últimos 20 datos por sensor
- **Galería de imágenes** con las últimas 5 capturas
- **Registro de eventos** cronológico del sistema

### Umbrales de Detección

| Estado | Condición |
|--------|-----------|
| **Normal** | Temperatura < 45°C y Luz < 800 lux |
| **Alerta** | Temperatura ≥ 45°C o Luz ≥ 800 lux |
| **Peligro** | Temperatura ≥ 55°C o Luz ≥ 1000 lux |
| **Fuego Confirmado** | Peligro + Análisis de imagen positivo (≥3% píxeles de fuego) |

Los umbrales son configurables editando las constantes en `server.py`:

```python
UMBRALES = {
    "temp_alerta": 45.0,
    "temp_peligro": 55.0,
    "luz_alerta": 800,
    "luz_peligro": 1000
}
```

## API REST

### Endpoints Principales

| Método | Endpoint | Descripción |
|--------|----------|-------------|
| `GET` | `/api/estado` | Estado global del sistema y última lectura |
| `POST` | `/api/sensores` | Enviar datos desde Arduino |
| `POST` | `/api/upload` | Subir imagen desde cámara |
| `GET` | `/api/eventos` | Log de eventos del sistema |
| `GET` | `/api/historico` | Histórico de lecturas de sensores |
| `GET` | `/api/ultimas-fotos` | URLs de últimas capturas |
| `GET` | `/dashboard` | Interfaz web de monitoreo |
| `GET` | `/docs` | Documentación interactiva de la API |

### Ejemplo de Uso

```bash
# Enviar datos de sensores (desde Arduino)
curl -X POST http://localhost:8000/api/sensores \
  -H "Content-Type: application/json" \
  -d '{
    "temperatura": 48.5,
    "luz": 850,
    "humedad": 35.2,
    "presion": 1013.25
  }'

# Obtener estado actual
curl http://localhost:8000/api/estado
```

## Testing y Simulación

El proyecto incluye scripts para probar sin hardware:

```bash
# Simular Arduino enviando datos cada 5 segundos
python simulate_arduino.py

# Simular condición de peligro inmediata
python test_simulate_danger.py
```

## Base de Datos

El sistema utiliza SQLite (`fire_detection.db`) con 3 tablas principales:

### Tabla: lecturas_sensores
Almacena todas las lecturas de sensores con timestamp.

### Tabla: eventos
Registra eventos importantes (alertas, peligros, fuegos confirmados).

### Tabla: analisis_ia
Guarda resultados del análisis de imágenes con nivel de confianza.

Puedes consultar la base de datos con:

```bash
sqlite3 fire_detection.db
sqlite> SELECT * FROM eventos ORDER BY timestamp DESC LIMIT 10;
```

## Seguridad

- **IMPORTANTE**: Nunca subas `telegram_config.py` con tus credenciales reales
- El archivo `.gitignore` está configurado para excluir información sensible
- Para producción, considera usar variables de entorno:

```bash
export TELEGRAM_BOT_TOKEN="tu_token"
export TELEGRAM_CHAT_ID="tu_chat_id"
```

- Implementa HTTPS si expones el servidor públicamente
- Considera autenticación para el dashboard en entornos públicos

## Estructura del Proyecto

```
fuego_detector_server/
├── server.py                    # Servidor FastAPI principal
├── mqtt_config.py               # Configuración cliente MQTT
├── telegram_config.py.example   # Plantilla configuración Telegram
├── camera_mqtt_android.py       # Script para cámara Android/Termux
├── camera_server_android.py     # Script alternativo HTTP
├── requirements.txt             # Dependencias Python
├── .gitignore                   # Archivos ignorados en Git
├── LICENSE                      # Licencia MIT
├── README.md                    # Este archivo
├── CONTRIBUTING.md              # Guía de contribución
├── informe_proyecto.tex         # Informe técnico LaTeX
├── arduino_code/                # Código Arduino
│   └── fire_detection_mkr_mqtt/ # Sketch principal con MQTT
├── models/                      # Módulo de análisis IA
│   └── script-IA.py            # Análisis de imágenes HSV
├── templates/                   # Templates HTML
│   └── dashboard.html          # Dashboard web interactivo
├── static/                      # Archivos estáticos (CSS/JS)
├── uploads/                     # Imágenes y audio capturados (no en Git)
│   ├── images/
│   └── audio/
└── logs/                        # Logs del sistema (no en Git)
```

## Roadmap y Mejoras Futuras

- [ ] **Integrar modelo de Deep Learning**: MobileNetV2 o YOLOv8 para >90% precisión
- [ ] **Detección de humo**: Agregar sensor MQ-2 y análisis de humo en imágenes
- [ ] **Red mesh multi-nodo**: Desplegar múltiples Arduino en diferentes ubicaciones
- [ ] **App móvil nativa**: Notificaciones push para Android/iOS
- [ ] **Integración con sistemas de extinción**: Activar rociadores automáticamente
- [ ] **Análisis predictivo**: Machine Learning para detectar patrones pre-incendio
- [ ] **Soporte para cámaras IP**: Integrar cámaras RTSP/ONVIF
- [ ] **Panel de administración**: Gestión de múltiples instalaciones
- [ ] **Exportación de reportes**: PDF con estadísticas y análisis

## Documentación Adicional

- **Informe técnico completo**: Ver `informe_proyecto.tex` (documento LaTeX de 30+ páginas)
- **Código Arduino detallado**: Ver `arduino_code/README_ARDUINO.md`
- **Análisis de imágenes**: Documentación en `models/script-IA.py`

## Contribuciones

Las contribuciones son bienvenidas. Por favor:

1. Lee [CONTRIBUTING.md](CONTRIBUTING.md)
2. Haz fork del proyecto
3. Crea una rama para tu feature (`git checkout -b feature/AmazingFeature`)
4. Commit tus cambios (`git commit -m 'Add: nueva funcionalidad X'`)
5. Push a la rama (`git push origin feature/AmazingFeature`)
6. Abre un Pull Request

## Problemas Conocidos

- **Termux**: En algunos dispositivos Android, `termux-camera-photo` puede requerir permisos adicionales
- **MQTT**: Conexión puede fallar si hay firewall bloqueando puerto 1883
- **Dashboard**: En navegadores muy antiguos, Chart.js puede no funcionar correctamente

## FAQ

**P: ¿Puedo usar ESP32 en lugar de Arduino Uno?**  
R: Sí, el código es compatible. ESP32 tiene ventaja de WiFi integrado.

**P: ¿Funciona sin cámara?**  
R: Sí, el sistema detecta con sensores, pero la cámara mejora la precisión.

**P: ¿Puedo usar otra app en lugar de Termux?**  
R: Sí, puedes desarrollar una app Android nativa o usar IP Webcam.

**P: ¿Cómo despliego en producción?**  
R: Usa servicios como Heroku, Railway.app o un VPS con systemd para mantener el servidor activo.

## Licencia

Este proyecto está bajo la Licencia MIT - ver el archivo [LICENSE](LICENSE) para más detalles.

## Autores

- **Universidad Nacional de San Agustín de Arequipa**
- Facultad de Ingeniería de Producción y Servicios
- Escuela Profesional de Ciencia de la computación
- Curso: Internet de las Cosas (IoT)

## Agradecimientos

- Comunidad de Arduino y FastAPI por la documentación
- Datasets de incendios: D-Fire, Fire-Smoke-Detection-Dataset
- HiveMQ por proporcionar broker MQTT público y gratuito
- Chart.js por las hermosas visualizaciones
- Termux por hacer posible ejecutar Python en Android

## Contacto

Para preguntas, sugerencias o reportar bugs:

- Abre un [issue](https://github.com/Ion25/fuego_detector_server/issues) en GitHub
- Revisa la documentación completa en el repositorio

---

**Si este proyecto te fue útil, considera darle una estrella en GitHub!**

**Desarrollado para la seguridad y protección contra incendios**
