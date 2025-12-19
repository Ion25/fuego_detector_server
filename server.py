"""
Servidor Backend - Sistema IoT de Detección de Incendios
Universidad Nacional de San Agustín - Arequipa, Perú

Flujo del sistema:
1. Arduino envía datos de sensores continuamente
2. Servidor evalúa umbrales internamente
3. Si detecta peligro, solicita captura al smartphone
4. Smartphone envía foto/audio
5. Servidor analiza con IA
6. Decisión final: fuego confirmado o falsa alarma
"""

from fastapi import FastAPI, HTTPException, File, UploadFile, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, FileResponse
from pydantic import BaseModel
from typing import Optional, List
import uvicorn
import json
import sqlite3
from datetime import datetime
import base64
import os
from pathlib import Path

# Importar funciones de Telegram
from telegram_config import enviar_mensaje_telegram, notificar_fuego_confirmado

# Importar funciones de MQTT
from mqtt_config import (
    inicializar_mqtt, 
    set_callback_sensores, 
    set_callback_multimedia,
    solicitar_captura_mqtt,
    detener_mqtt
)

# Importar requests para comunicación con cámara Android (HTTP como respaldo)
import requests


# ============================================================================
# CONFIGURACIÓN INICIAL
# ============================================================================

app = FastAPI(title="Fire Detection Server", version="1.0.0")

# Habilitar CORS para peticiones desde Arduino y smartphone
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configuración de umbrales
UMBRALES = {
    "temp_alerta": 45.0,
    "temp_peligro": 55.0,
    "luz_alerta": 800,
    "luz_peligro": 1000
}

# Configuración de cámara Android
CAMARA_ANDROID_URL = "http://192.168.1.100:8080"  # Cambiar a la IP del teléfono
DURACION_AUDIO = 5  # Segundos de grabación de audio

# Estado global del sistema
ESTADO_SISTEMA = {
    "estado_actual": "Normal",  # Normal, Alerta, Peligro, Fuego_Confirmado
    "requiere_captura": False,
    "ultima_lectura": None,
    "ultima_foto": None,
    "ultimo_analisis_ia": None
}

# ============================================================================
# CONFIGURACIÓN DE DIRECTORIOS
# ============================================================================

# Crear estructura de carpetas
BASE_DIR = Path(__file__).parent
UPLOADS_DIR = BASE_DIR / "uploads"
IMAGES_DIR = UPLOADS_DIR / "images"
AUDIO_DIR = UPLOADS_DIR / "audio"
LOGS_DIR = BASE_DIR / "logs"
MODELS_DIR = BASE_DIR / "models"
STATIC_DIR = BASE_DIR / "static"
TEMPLATES_DIR = BASE_DIR / "templates"

# Crear directorios si no existen
for directory in [UPLOADS_DIR, IMAGES_DIR, AUDIO_DIR, LOGS_DIR, MODELS_DIR, STATIC_DIR, TEMPLATES_DIR]:
    directory.mkdir(parents=True, exist_ok=True)

# Montar directorio de uploads como archivos estáticos
app.mount("/uploads", StaticFiles(directory=str(UPLOADS_DIR)), name="uploads")

# ============================================================================
# MQTT - Callback y Configuración
# ============================================================================

def procesar_datos_mqtt(datos: dict):
    """
    Callback que se llama cuando llegan datos del Arduino vía MQTT.
    Procesa los datos exactamente igual que el endpoint HTTP.
    """
    try:
        print(f"\n📡 Datos recibidos vía MQTT: Temp={datos.get('temperatura')}°C, Luz={datos.get('luz')} lux")
        
        # Crear objeto DatosSensores
        datos_sensores = DatosSensores(
            temperatura=datos.get('temperatura', 0.0),
            luz=datos.get('luz', 0.0),
            humedad=datos.get('humedad', 0.0),
            presion=datos.get('presion', 0.0)
        )
        
        # Evaluar estado según umbrales
        estado = evaluar_estado(datos_sensores.temperatura, datos_sensores.luz)
        
        # Actualizar estado global
        ESTADO_SISTEMA["ultima_lectura"] = {
            "temperatura": datos_sensores.temperatura,
            "luz": datos_sensores.luz,
            "humedad": datos_sensores.humedad,
            "presion": datos_sensores.presion,
            "timestamp": datetime.now().isoformat()
        }
        
        estado_anterior = ESTADO_SISTEMA["estado_actual"]
        ESTADO_SISTEMA["estado_actual"] = estado
        
        # Guardar en base de datos
        guardar_lectura_sensores(datos_sensores, estado)
        
        # Si cambió a estado Peligro, activar solicitud de captura
        if estado == "Peligro" and estado_anterior != "Peligro":
            ESTADO_SISTEMA["requiere_captura"] = True
            registrar_evento(
                "PELIGRO_DETECTADO",
                f"Umbrales críticos superados: Temp={datos_sensores.temperatura}°C, Luz={datos_sensores.luz} lux",
                {"temperatura": datos_sensores.temperatura, "luz": datos_sensores.luz}
            )
            print(f"🚨 PELIGRO DETECTADO (MQTT) - Activando captura automática")
            
            # 🎥 Solicitar captura automática a la cámara Android vía MQTT
            try:
                solicitar_captura_mqtt()
                print("✓ Comando MQTT enviado a cámara Android")
            except Exception as e:
                print(f"⚠️  Error al solicitar captura vía MQTT: {e}")
        
        print(f"✓ Estado actual: {estado}")
        
    except Exception as e:
        print(f"✗ Error procesando datos MQTT: {e}")

def procesar_multimedia_mqtt(datos: dict):
    """
    Callback que se llama cuando llegan foto + audio desde la cámara por MQTT.
    Procesa los datos exactamente igual que el endpoint HTTP /api/upload.
    """
    try:
        print(f"\n📸 Multimedia recibida vía MQTT")
        print(f"   Dispositivo: {datos.get('dispositivo')}")
        print(f"   Timestamp: {datos.get('timestamp')}")
        
        # Guardar la foto
        imagen_base64 = datos.get('imagen')
        if not imagen_base64:
            print("✗ No se recibió imagen")
            return
        
        timestamp_str = datetime.now().strftime("%Y%m%d_%H%M%S")
        imagen_filename = f"captura_{timestamp_str}.jpg"
        imagen_path = IMAGES_DIR / imagen_filename
        
        # Decodificar y guardar imagen
        try:
            imagen_bytes = base64.b64decode(imagen_base64)
            with open(imagen_path, 'wb') as f:
                f.write(imagen_bytes)
            print(f"💾 Imagen guardada: {imagen_path}")
            
            # Guardar ruta relativa para uso público (serve static files desde /uploads)
            imagen_rel = f"uploads/images/{imagen_filename}"
            # Actualizar estado global con ruta relativa
            ESTADO_SISTEMA["ultima_foto"] = imagen_rel
            
        except Exception as e:
            print(f"✗ Error al guardar imagen: {e}")
            return
        
        # Guardar audio si existe
        audio_path = None
        audio_rel = None
        audio_base64 = datos.get('audio')
        if audio_base64:
            try:
                audio_filename = f"audio_{timestamp_str}.wav"
                audio_path = AUDIO_DIR / audio_filename
                audio_bytes = base64.b64decode(audio_base64)
                with open(audio_path, 'wb') as f:
                    f.write(audio_bytes)
                print(f"💾 Audio guardado: {audio_path}")
                audio_rel = f"uploads/audio/{audio_filename}"
            except Exception as e:
                print(f"⚠️  Error al guardar audio: {e}")

        # Analizar con IA (usar ruta absoluta para el análisis)
        print(f"🤖 Analizando imagen con IA...")
        resultado_ia = predecir_fuego(str(imagen_path))

        fuego_detectado = resultado_ia["fuego_detectado"]
        confianza = resultado_ia["confianza"]

        print(f"   Fuego detectado: {'SÍ' if fuego_detectado else 'NO'}")
        print(f"   Confianza: {confianza:.2f}%")

        # Guardar análisis en base de datos (usar rutas relativas para imágenes/audios)
        conn = sqlite3.connect('fire_detection.db')
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO analisis_ia (timestamp, imagen_path, audio_path, fuego_detectado, confianza, datos_sensores)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (
            datetime.now().isoformat(),
            imagen_rel,
            audio_rel if audio_rel else None,
            1 if fuego_detectado else 0,
            confianza,
            json.dumps(ESTADO_SISTEMA.get("ultima_lectura"))
        ))
        conn.commit()
        conn.close()

        # Actualizar estado del sistema si confirma fuego
        if fuego_detectado and confianza >= 75:
            ESTADO_SISTEMA["estado_actual"] = "Fuego_Confirmado"
            ESTADO_SISTEMA["ultimo_analisis_ia"] = resultado_ia
            
            registrar_evento(
                "FUEGO_CONFIRMADO",
                f"IA confirmó presencia de fuego con {confianza:.1f}% de confianza",
                resultado_ia
            )
            print(f"🔥 FUEGO CONFIRMADO por IA (MQTT)")

            # Enviar notificación por Telegram solo cuando la IA confirma fuego
            try:
                notificar_fuego_confirmado(confianza * 100, imagen_url=imagen_rel)
            except Exception as e:
                print(f"⚠️ Error al notificar por Telegram: {e}")
        else:
            ESTADO_SISTEMA["requiere_captura"] = False
            registrar_evento(
                "FALSA_ALARMA",
                f"IA no detectó fuego ({confianza:.1f}% confianza)",
                resultado_ia
            )
            print(f"✓ Falsa alarma descartada (MQTT)")
        
    except Exception as e:
        print(f"✗ Error procesando multimedia MQTT: {e}")

@app.on_event("startup")
async def startup_event():
    """Inicializar MQTT cuando arranca el servidor"""
    print("\n" + "=" * 60)
    print("🚀 Iniciando Fire Detection Server")
    print("=" * 60)
    
    # Inicializar base de datos
    init_database()
    print("✓ Base de datos inicializada")

    # Normalizar rutas antiguas en la base de datos (convertir absolutas a relativas)
    try:
        normalize_db_paths()
    except Exception as e:
        print(f"⚠️  Error ejecutando normalización de rutas en startup: {e}")

    # Cargar modelo IA (intentará cargar TFLite/Keras si está disponible)
    try:
        cargar_modelo_ia()
    except Exception as e:
        print(f"⚠️ Error cargando modelo IA en startup: {e}")

    # Inicializar MQTT
    print("\n🔌 Inicializando cliente MQTT...")
    mqtt_client = inicializar_mqtt()

    if mqtt_client:
        # Configurar callback para procesar datos de sensores
        set_callback_sensores(procesar_datos_mqtt)
        # Configurar callback para procesar multimedia
        set_callback_multimedia(procesar_multimedia_mqtt)
        print("✓ Cliente MQTT configurado")
        print(f"✓ Esperando datos del Arduino en topic: unsa/fire_detection/sensores")
    else:
        print("⚠️  No se pudo inicializar MQTT. El servidor seguirá funcionando con HTTP.")
    
    print("\n✓ Servidor listo")
    print("=" * 60 + "\n")

@app.on_event("shutdown")
async def shutdown_event():
    """Detener MQTT cuando se cierra el servidor"""
    print("\n⏹️  Cerrando conexiones...")
    detener_mqtt()
    print("✓ Servidor detenido")

# ============================================================================
# MODELOS DE DATOS (Pydantic)
# ============================================================================

class DatosSensores(BaseModel):
    temperatura: float
    luz: float
    humedad: float
    presion: float

class UploadMultimedia(BaseModel):
    imagen: str  # Base64
    audio: Optional[str] = None  # Base64 (opcional)
    timestamp: str

class ConfigUmbrales(BaseModel):
    temp_alerta: Optional[float] = None
    temp_peligro: Optional[float] = None
    luz_alerta: Optional[float] = None
    luz_peligro: Optional[float] = None

# ============================================================================
# INICIALIZACIÓN DE BASE DE DATOS
# ============================================================================

def init_database():
    """Crea las tablas necesarias en SQLite"""
    conn = sqlite3.connect('fire_detection.db')
    cursor = conn.cursor()
    
    # Tabla de lecturas de sensores
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS lecturas_sensores (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            temperatura REAL,
            luz REAL,
            humedad REAL,
            presion REAL,
            estado TEXT
        )
    ''')
    
    # Tabla de eventos (alertas, peligro, fuego confirmado)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS eventos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            tipo_evento TEXT,
            descripcion TEXT,
            datos_json TEXT
        )
    ''')
    
    # Tabla de resultados de IA
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS analisis_ia (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            imagen_path TEXT,
            audio_path TEXT,
            fuego_detectado INTEGER,
            confianza REAL,
            datos_sensores TEXT
        )
    ''')
    
    conn.commit()
    conn.close()
    print("✅ Base de datos inicializada correctamente")

def normalize_db_paths():
    """
    Convierte entradas antiguas en la tabla analisis_ia que contienen rutas absolutas
    (por ejemplo: "/home/arecles/.../uploads/images/xxx.jpg") a rutas relativas
    que el servidor sirve en /uploads (por ejemplo: "uploads/images/xxx.jpg").
    """
    try:
        conn = sqlite3.connect('fire_detection.db')
        cursor = conn.cursor()
        cursor.execute("SELECT id, imagen_path, audio_path FROM analisis_ia")
        rows = cursor.fetchall()
        updates = 0
        for rid, ipath, apath in rows:
            new_ipath = None
            new_apath = None
            if ipath:
                # Si comienza con / o contiene el base dir, normalizar
                if ipath.startswith('/') or str(BASE_DIR) in ipath:
                    new_ipath = f"uploads/images/{os.path.basename(ipath)}"
            if apath:
                if apath.startswith('/') or str(BASE_DIR) in apath:
                    new_apath = f"uploads/audio/{os.path.basename(apath)}"
            if new_ipath or new_apath:
                cursor.execute('''
                    UPDATE analisis_ia
                    SET imagen_path = COALESCE(?, imagen_path),
                        audio_path = COALESCE(?, audio_path)
                    WHERE id = ?
                ''', (new_ipath, new_apath, rid))
                updates += 1
        conn.commit()
        conn.close()
        print(f"✅ Normalización de rutas en DB completada. Filas actualizadas: {updates}")
    except Exception as e:
        print(f"⚠️ Error normalizando rutas en DB: {e}")

# ============================================================================
# FUNCIONES AUXILIARES
# ============================================================================

def evaluar_estado(temperatura: float, luz: float) -> str:
    """
    Evalúa el estado del sistema según los umbrales
    
    Returns:
        "Normal", "Alerta" o "Peligro"
    """
    # Estado PELIGRO (umbrales críticos)
    if temperatura >= UMBRALES["temp_peligro"] or luz >= UMBRALES["luz_peligro"]:
        return "Peligro"
    
    # Estado ALERTA (umbrales elevados)
    if temperatura >= UMBRALES["temp_alerta"] or luz >= UMBRALES["luz_alerta"]:
        return "Alerta"
    
    # Estado NORMAL
    return "Normal"

def solicitar_captura_automatica():
    """
    Envía comando HTTP a la cámara Android para capturar foto + audio automáticamente.
    La cámara capturará y subirá los datos al servidor sin intervención manual.
    """
    try:
        print(f"\n📱 Solicitando captura automática a la cámara Android...")
        print(f"   URL: {CAMARA_ANDROID_URL}/capturar")
        
        # Enviar comando POST a la cámara
        response = requests.post(
            f"{CAMARA_ANDROID_URL}/capturar",
            json={"duracion_audio": DURACION_AUDIO},
            timeout=2  # Timeout corto, la cámara procesará en background
        )
        
        if response.status_code == 200:
            print(f"✓ Comando de captura enviado exitosamente")
            print(f"   La cámara capturará foto y audio automáticamente")
            return True
        else:
            print(f"⚠️  Error al enviar comando: {response.status_code}")
            return False
            
    except requests.exceptions.Timeout:
        print(f"⚠️  Timeout al conectar con la cámara (comando enviado)")
        # El timeout es normal, la cámara procesará en background
        return True
        
    except requests.exceptions.ConnectionError:
        print(f"✗ No se pudo conectar con la cámara Android")
        print(f"   Verifica que esté ejecutando camera_server_android.py")
        print(f"   URL configurada: {CAMARA_ANDROID_URL}")
        return False
        
    except Exception as e:
        print(f"✗ Error al solicitar captura: {e}")
        return False

def guardar_lectura_sensores(datos: DatosSensores, estado: str):
    """Guarda una lectura de sensores en la base de datos"""
    conn = sqlite3.connect('fire_detection.db')
    cursor = conn.cursor()
    
    timestamp = datetime.now().isoformat()
    cursor.execute('''
        INSERT INTO lecturas_sensores (timestamp, temperatura, luz, humedad, presion, estado)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', (timestamp, datos.temperatura, datos.luz, datos.humedad, datos.presion, estado))
    
    conn.commit()
    conn.close()

def registrar_evento(tipo: str, descripcion: str, datos_extra: dict = None):
    """Registra un evento en la base de datos"""
    conn = sqlite3.connect('fire_detection.db')
    cursor = conn.cursor()
    
    timestamp = datetime.now().isoformat()
    datos_json = json.dumps(datos_extra) if datos_extra else None
    
    cursor.execute('''
        INSERT INTO eventos (timestamp, tipo_evento, descripcion, datos_json)
        VALUES (?, ?, ?, ?)
    ''', (timestamp, tipo, descripcion, datos_json))
    
    conn.commit()
    conn.close()
    
    # También guardar en archivo de log
    log_file = LOGS_DIR / f"eventos_{datetime.now().strftime('%Y-%m-%d')}.log"
    with open(log_file, 'a') as f:
        f.write(f"[{timestamp}] {tipo}: {descripcion}\n")

def guardar_imagen_base64(imagen_base64: str) -> str:
    """
    Guarda una imagen en formato base64 y retorna la ruta
    
    Returns:
        Ruta relativa del archivo guardado
    """
    # Remover el prefijo data:image/...;base64, si existe
    if ',' in imagen_base64:
        imagen_base64 = imagen_base64.split(',')[1]
    
    # Decodificar base64
    imagen_bytes = base64.b64decode(imagen_base64)
    
    # Generar nombre de archivo con timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"captura_{timestamp}.jpg"
    filepath = IMAGES_DIR / filename
    
    # Guardar archivo
    with open(filepath, 'wb') as f:
        f.write(imagen_bytes)
    
    return f"uploads/images/{filename}"

def guardar_audio_base64(audio_base64: str) -> str:
    """
    Guarda un audio en formato base64 y retorna la ruta
    
    Returns:
        Ruta relativa del archivo guardado
    """
    # Remover el prefijo si existe
    if ',' in audio_base64:
        audio_base64 = audio_base64.split(',')[1]
    
    # Decodificar base64
    audio_bytes = base64.b64decode(audio_base64)
    
    # Generar nombre de archivo con timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"audio_{timestamp}.wav"
    filepath = AUDIO_DIR / filename
    
    # Guardar archivo
    with open(filepath, 'wb') as f:
        f.write(audio_bytes)
    
    return f"uploads/audio/{filename}"

# ============================================================================
# FUNCIONES DE IA (PLACEHOLDER)
# ============================================================================

# Variables globales para el modelo IA
MODEL = None
MODEL_TYPE = None  # 'keras' | 'tflite' | None
MODEL_INPUT_SHAPE = (224, 224)  # Valor por defecto, se ajustará si el modelo indica otra cosa


def cargar_modelo_ia():
    """
    Intenta cargar un modelo IA en el siguiente orden:
      1) models/fire_model.h5 (Keras/TensorFlow)
      2) models/fire_model.tflite (TFLite)
    Si no existe ningún modelo o las dependencias faltan, devuelve None y el sistema usará
    un detector heurístico basado en color para pruebas.
    """
    global MODEL, MODEL_TYPE, MODEL_INPUT_SHAPE

    # Intentar cargar Keras/TensorFlow
    try:
        import tensorflow as tf
        keras_model_path = MODELS_DIR / 'fire_model.h5'
        if keras_model_path.exists():
            print(f"🔁 Cargando modelo Keras desde {keras_model_path}")
            MODEL = tf.keras.models.load_model(str(keras_model_path))
            # Obtener shape de entrada si está disponible
            try:
                input_shape = MODEL.input_shape
                # input_shape puede ser (None, h, w, c)
                if isinstance(input_shape, tuple) and len(input_shape) >= 3:
                    MODEL_INPUT_SHAPE = (input_shape[1], input_shape[2])
            except Exception:
                pass
            MODEL_TYPE = 'keras'
            print("✅ Modelo Keras cargado correctamente")
            return MODEL
    except Exception as e:
        print(f"⚠️ No se pudo cargar TensorFlow/Keras o modelo .h5 no encontrado: {e}")

    # Intentar cargar TFLite
    try:
        try:
            # Primero intentar tflite_runtime (más ligero)
            import tflite_runtime.interpreter as tflite
            Interpreter = tflite.Interpreter
        except Exception:
            # Fallback a TF Lite incluido en tensorflow
            import tensorflow as tf
            Interpreter = tf.lite.Interpreter

        tflite_model_path = MODELS_DIR / 'fire_model.tflite'
        if tflite_model_path.exists():
            print(f"🔁 Cargando modelo TFLite desde {tflite_model_path}")
            interpreter = Interpreter(model_path=str(tflite_model_path))
            interpreter.allocate_tensors()
            MODEL = interpreter
            MODEL_TYPE = 'tflite'
            # Intentar obtener shape de entrada
            try:
                input_details = interpreter.get_input_details()
                shape = input_details[0]['shape']
                if len(shape) >= 3:
                    MODEL_INPUT_SHAPE = (int(shape[1]), int(shape[2]))
            except Exception:
                pass
            print("✅ Modelo TFLite cargado correctamente")
            return MODEL
    except Exception as e:
        print(f"⚠️ No se pudo cargar TFLite: {e}")

    # Si llegamos aquí, no se cargó ningún modelo
    MODEL = None
    MODEL_TYPE = None
    print("⚠️ No se encontró ningún modelo IA. Usando heurística de color como fallback.")
    return None


def predecir_fuego(imagen_path: str) -> dict:
    """
    Analiza una imagen para detectar fuego.

    Args:
        imagen_path: Ruta absoluta o relativa a la imagen (puede ser 'uploads/images/xxx.jpg')

    Returns:
        dict con 'fuego_detectado' (bool) y 'confianza' (float entre 0 y 1)
    """
    global MODEL, MODEL_TYPE, MODEL_INPUT_SHAPE

    # Resolver ruta de archivo: si es relativa dentro de uploads, convertir a path absoluto
    try:
        img_path = imagen_path
        if not os.path.isabs(img_path):
            # Si se proporcionó la ruta relativa guardada en DB (uploads/...), unimos con BASE_DIR
            candidate = BASE_DIR / img_path
            if candidate.exists():
                img_path = str(candidate)
            else:
                # Intentar con solo basename en uploads/images
                candidate2 = IMAGES_DIR / os.path.basename(img_path)
                if candidate2.exists():
                    img_path = str(candidate2)
        if not os.path.exists(img_path):
            raise FileNotFoundError(f"Archivo de imagen no encontrado: {img_path}")
    except Exception as e:
        print(f"⚠️ predecir_fuego: error resolviendo ruta de imagen: {e}")
        return {"fuego_detectado": False, "confianza": 0.0}

    # Intentar inferencia con modelo cargado
    try:
        # Importar PIL y numpy solo cuando sea necesario
        from PIL import Image
        import numpy as np

        if MODEL and MODEL_TYPE == 'keras':
            # Preprocesar imagen según tamaño del modelo
            img = Image.open(img_path).convert('RGB')
            img_resized = img.resize(MODEL_INPUT_SHAPE)
            arr = np.asarray(img_resized).astype('float32') / 255.0
            batch = np.expand_dims(arr, axis=0)
            preds = MODEL.predict(batch)
            # Asumimos clasificador binario que devuelve probabilidad de clase 'fuego'
            # TensorFlow puede retornar una matriz (batch,1) o (batch,2)
            if preds.ndim == 2 and preds.shape[1] == 2:
                prob = float(preds[0,1])
            else:
                prob = float(preds[0,0])
            fuego = prob >= 0.5
            return {"fuego_detectado": bool(fuego), "confianza": max(0.0, min(1.0, prob))}

        elif MODEL and MODEL_TYPE == 'tflite':
            # Usar el interpreter TFLite
            import numpy as np
            from PIL import Image
            interpreter = MODEL
            input_details = interpreter.get_input_details()
            output_details = interpreter.get_output_details()

            img = Image.open(img_path).convert('RGB')
            img_resized = img.resize(MODEL_INPUT_SHAPE)
            arr = np.asarray(img_resized).astype('float32') / 255.0
            input_data = np.expand_dims(arr, axis=0)

            # Algunos modelos TFLite esperan uint8
            if input_details[0]['dtype'] == np.uint8:
                input_scale, input_zero_point = input_details[0].get('quantization', (1.0, 0))
                if input_scale and input_zero_point is not None:
                    input_data = (input_data / input_scale + input_zero_point).astype(np.uint8)

            interpreter.set_tensor(input_details[0]['index'], input_data)
            interpreter.invoke()
            output_data = interpreter.get_tensor(output_details[0]['index'])
            # Interpretar salida similar a Keras
            if output_data.ndim == 2 and output_data.shape[1] == 2:
                prob = float(output_data[0,1])
            else:
                prob = float(output_data[0,0])
            fuego = prob >= 0.5
            return {"fuego_detectado": bool(fuego), "confianza": max(0.0, min(1.0, prob))}

    except Exception as e:
        print(f"⚠️ Error durante inferencia con modelo IA: {e}")
        # Caer a heurística abajo

    # Fallback heurístico basado en color (útil para pruebas sin modelo)
    try:
        from PIL import Image
        import numpy as np

        img = Image.open(img_path).convert('RGB')
        arr = np.asarray(img)
        # Convertir a HSV para detectar tonos rojizos/amarillos típicos de fuego
        import cv2
        hsv = cv2.cvtColor(arr, cv2.COLOR_RGB2HSV)
        h, s, v = hsv[:, :, 0], hsv[:, :, 1], hsv[:, :, 2]
        # Rango de hueso que puede representar fuego: 0-50 (rojos-amarillos)
        mask = ((h <= 50) & (s >= 80) & (v >= 80))
        ratio = float(np.sum(mask)) / (arr.shape[0] * arr.shape[1])

        # Mapear ratio a confianza (ajustable)
        confianza = min(1.0, ratio * 10)  # si 10% de pixeles, confianza ~1.0
        fuego = confianza >= 0.2  # umbral bajo para heurística
        print(f"🔎 Heurística de color: ratio={ratio:.4f}, confianza={confianza:.3f}")
        return {"fuego_detectado": bool(fuego), "confianza": confianza}

    except Exception as e:
        print(f"⚠️ Heurística falló: {e}")
        return {"fuego_detectado": False, "confianza": 0.0}

# ============================================================================
# ENDPOINTS DE LA API
# ============================================================================

@app.get("/")
async def root():
    """Endpoint raíz - redirige al dashboard"""
    return {"message": "Fire Detection Server API", "version": "1.0.0"}

@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard():
    """Sirve el dashboard HTML"""
    dashboard_file = TEMPLATES_DIR / "dashboard.html"
    if dashboard_file.exists():
        return FileResponse(dashboard_file)
    else:
        return "<h1>Dashboard en desarrollo</h1>"

# ----------------------------------------------------------------------------
# ENDPOINTS PARA ARDUINO
# ----------------------------------------------------------------------------

@app.post("/api/sensores")
async def recibir_datos_sensores(datos: DatosSensores):
    """
    Recibe datos de sensores desde el Arduino
    
    El Arduino envía:
    {
        "temperatura": 48.5,
        "luz": 920,
        "humedad": 45.3,
        "presion": 1013.25
    }
    """
    print(f"📡 Datos recibidos del Arduino: Temp={datos.temperatura}°C, Luz={datos.luz} lux")
    
    # Evaluar estado según umbrales
    estado = evaluar_estado(datos.temperatura, datos.luz)
    
    # Actualizar estado global
    ESTADO_SISTEMA["ultima_lectura"] = {
        "temperatura": datos.temperatura,
        "luz": datos.luz,
        "humedad": datos.humedad,
        "presion": datos.presion,
        "timestamp": datetime.now().isoformat()
    }
    
    estado_anterior = ESTADO_SISTEMA["estado_actual"]
    ESTADO_SISTEMA["estado_actual"] = estado
    
    # Guardar en base de datos
    guardar_lectura_sensores(datos, estado)
    
    # Si cambió a estado Peligro, activar solicitud de captura
    if estado == "Peligro" and estado_anterior != "Peligro":
        ESTADO_SISTEMA["requiere_captura"] = True
        registrar_evento(
            "PELIGRO_DETECTADO",
            f"Umbrales críticos superados: Temp={datos.temperatura}°C, Luz={datos.luz} lux",
            {"temperatura": datos.temperatura, "luz": datos.luz}
        )
        print(f"🚨 PELIGRO DETECTADO - Activando captura automática")
        
        # 🎥 Solicitar captura automática a la cámara Android vía MQTT
        try:
            solicitar_captura_mqtt()
            print("✓ Comando MQTT enviado a cámara Android")
        except Exception as e:
            print(f"⚠️  Error al solicitar captura vía MQTT: {e}")
        
    # Respuesta simple (el Arduino no necesita instrucciones)
    return {
        "status": "ok",
        "estado": estado,
        "timestamp": datetime.now().isoformat()
    }

@app.get("/api/estado")
async def obtener_estado():
    """
    Devuelve el estado actual del sistema
    """
    return {
        "estado_actual": ESTADO_SISTEMA["estado_actual"],
        "ultima_lectura": ESTADO_SISTEMA["ultima_lectura"],
        "requiere_captura": ESTADO_SISTEMA["requiere_captura"],
        "ultima_foto": ESTADO_SISTEMA["ultima_foto"],
        "umbrales": UMBRALES
    }

@app.get("/api/umbrales")
async def obtener_umbrales():
    """Devuelve los umbrales configurados"""
    return UMBRALES

# ----------------------------------------------------------------------------
# ENDPOINTS PARA SMARTPHONE
# ----------------------------------------------------------------------------

@app.get("/api/solicitar-captura")
async def solicitar_captura():
    """
    El smartphone consulta si debe capturar foto/audio
    
    Responde:
    - capturar: true/false
    - estado: estado actual del sistema
    """
    requiere = ESTADO_SISTEMA["requiere_captura"]
    
    return {
        "capturar": requiere,
        "estado": ESTADO_SISTEMA["estado_actual"],
        "mensaje": "Captura requerida - posible fuego" if requiere else "No se requiere captura",
        "datos_sensores": ESTADO_SISTEMA["ultima_lectura"] if requiere else None
    }

@app.post("/api/upload")
async def upload_multimedia(datos: UploadMultimedia):
    """
    Recibe foto y audio desde el smartphone
    
    Formato esperado:
    {
        "imagen": "data:image/jpeg;base64,...",
        "audio": "data:audio/wav;base64,...",
        "timestamp": "2025-12-12 15:30:45"
    }
    """
    print(f"📸 Recibiendo captura del smartphone ({datos.timestamp})")
    
    try:
        # Guardar imagen
        imagen_path = guardar_imagen_base64(datos.imagen)
        print(f"✅ Imagen guardada: {imagen_path}")
        
        # Guardar audio (si existe)
        audio_path = None
        if datos.audio:
            audio_path = guardar_audio_base64(datos.audio)
            print(f"✅ Audio guardado: {audio_path}")
        
        # Actualizar estado
        ESTADO_SISTEMA["ultima_foto"] = imagen_path
        ESTADO_SISTEMA["requiere_captura"] = False
        
        # Registrar evento
        registrar_evento(
            "CAPTURA_RECIBIDA",
            "Foto y audio recibidos del smartphone",
            {"imagen": imagen_path, "audio": audio_path}
        )
        
        # EJECUTAR ANÁLISIS CON IA
        print("🤖 Analizando imagen con IA...")
        resultado_ia = predecir_fuego(imagen_path)
        
        # Guardar resultado en base de datos
        conn = sqlite3.connect('fire_detection.db')
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO analisis_ia (timestamp, imagen_path, audio_path, fuego_detectado, confianza, datos_sensores)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (
            datetime.now().isoformat(),
            imagen_path,
            audio_path,
            1 if resultado_ia["fuego_detectado"] else 0,
            resultado_ia["confianza"],
            json.dumps(ESTADO_SISTEMA["ultima_lectura"])
        ))
        conn.commit()
        conn.close()
        
        # DECISIÓN FINAL
        if resultado_ia["fuego_detectado"] and resultado_ia["confianza"] > 0.75:
            # ¡FUEGO CONFIRMADO!
            ESTADO_SISTEMA["estado_actual"] = "Fuego_Confirmado"
            ESTADO_SISTEMA["ultimo_analisis_ia"] = resultado_ia
            
            registrar_evento(
                "FUEGO_CONFIRMADO",
                f"IA confirmó presencia de fuego (confianza: {resultado_ia['confianza']:.2%})",
                resultado_ia
            )
            
            print(f"🔥 ¡FUEGO CONFIRMADO! Confianza: {resultado_ia['confianza']:.2%}")

            # Enviar notificación por Telegram solo cuando la IA confirma fuego
            try:
                # La función espera porcentaje (0-100)
                notificar_fuego_confirmado(resultado_ia['confianza'] * 100, imagen_url=imagen_path)
            except Exception as e:
                print(f"⚠️ Error al notificar por Telegram: {e}")

            # TODO: Enviar notificaciones (WhatsApp, Email)
            
            return {
                "status": "fuego_confirmado",
                "mensaje": "¡FUEGO DETECTADO!",
                "confianza": resultado_ia["confianza"],
                "imagen_guardada": imagen_path,
                "audio_guardado": audio_path
            }
        else:
            # Falsa alarma
            ESTADO_SISTEMA["estado_actual"] = "Normal"
            ESTADO_SISTEMA["ultimo_analisis_ia"] = resultado_ia
            
            registrar_evento(
                "FALSA_ALARMA",
                f"IA descartó presencia de fuego (confianza: {resultado_ia['confianza']:.2%})",
                resultado_ia
            )
            
            print(f"✅ Falsa alarma - No se detectó fuego (confianza: {resultado_ia['confianza']:.2%})")
            
            return {
                "status": "falsa_alarma",
                "mensaje": "No se detectó fuego",
                "confianza": resultado_ia["confianza"],
                "imagen_guardada": imagen_path,
                "audio_guardado": audio_path
            }
            
    except Exception as e:
        print(f"❌ Error procesando multimedia: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error procesando archivos: {str(e)}")

# ----------------------------------------------------------------------------
# ENDPOINTS DE CONFIGURACIÓN
# ----------------------------------------------------------------------------

@app.put("/api/config/umbrales")
async def actualizar_umbrales(config: ConfigUmbrales):
    """
    Actualiza los umbrales del sistema
    
    Permite modificar dinámicamente los valores de alerta y peligro
    """
    global UMBRALES
    
    if config.temp_alerta is not None:
        UMBRALES["temp_alerta"] = config.temp_alerta
    if config.temp_peligro is not None:
        UMBRALES["temp_peligro"] = config.temp_peligro
    if config.luz_alerta is not None:
        UMBRALES["luz_alerta"] = config.luz_alerta
    if config.luz_peligro is not None:
        UMBRALES["luz_peligro"] = config.luz_peligro
    
    registrar_evento("CONFIG_UMBRALES", "Umbrales actualizados", UMBRALES)
    print(f"⚙️  Umbrales actualizados: {UMBRALES}")
    
    return {
        "status": "ok",
        "umbrales_actualizados": UMBRALES
    }

@app.get("/api/historico")
async def obtener_historico(limit: int = 100):
    """
    Obtiene el histórico de lecturas de sensores
    
    Args:
        limit: Número máximo de registros a devolver (default: 100)
    """
    conn = sqlite3.connect('fire_detection.db')
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT timestamp, temperatura, luz, humedad, presion, estado
        FROM lecturas_sensores
        ORDER BY id DESC
        LIMIT ?
    ''', (limit,))
    
    resultados = cursor.fetchall()
    conn.close()
    
    historico = []
    for row in resultados:
        historico.append({
            "timestamp": row[0],
            "temperatura": row[1],
            "luz": row[2],
            "humedad": row[3],
            "presion": row[4],
            "estado": row[5]
        })
    
    return {
        "total": len(historico),
        "registros": historico
    }

@app.get("/api/eventos")
async def obtener_eventos(limit: int = 50):
    """
    Obtiene el log de eventos del sistema
    """
    conn = sqlite3.connect('fire_detection.db')
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT timestamp, tipo_evento, descripcion, datos_json
        FROM eventos
        ORDER BY id DESC
        LIMIT ?
    ''', (limit,))
    
    resultados = cursor.fetchall()
    conn.close()
    
    eventos = []
    for row in resultados:
        eventos.append({
            "timestamp": row[0],
            "tipo": row[1],
            "descripcion": row[2],
            "datos": json.loads(row[3]) if row[3] else None
        })
    
    return {
        "total": len(eventos),
        "eventos": eventos
    }

@app.get("/api/ultimas-fotos")
async def obtener_ultimas_fotos(limit: int = 5):
    """Devuelve las últimas `limit` fotos analizadas por la IA (rutas relativas)."""
    try:
        conn = sqlite3.connect('fire_detection.db')
        cursor = conn.cursor()
        cursor.execute('''
            SELECT imagen_path
            FROM analisis_ia
            WHERE imagen_path IS NOT NULL
            ORDER BY id DESC
            LIMIT ?
        ''', (limit,))
        rows = cursor.fetchall()
        conn.close()

        fotos = [row[0] for row in rows]
        return {
            "total": len(fotos),
            "fotos": fotos
        }
    except Exception as e:
        print(f"⚠️ Error obteniendo últimas fotos: {e}")
        return {"total": 0, "fotos": []}

# ============================================================================
# INICIALIZACIÓN Y EJECUCIÓN
# ============================================================================

if __name__ == "__main__":
    print("=" * 60)
    print("🔥 SERVIDOR DE DETECCIÓN DE INCENDIOS")
    print("   Universidad Nacional de San Agustín - Arequipa, Perú")
    print("=" * 60)
    
    # Inicializar base de datos
    init_database()
    
    # Cargar modelo de IA (placeholder)
    cargar_modelo_ia()
    
    print("\n📡 Iniciando servidor en http://0.0.0.0:5000")
    print("📊 Dashboard disponible en http://0.0.0.0:5000/dashboard")
    print("📖 Documentación API en http://0.0.0.0:5000/docs")
    print("\n✅ Servidor listo para recibir peticiones\n")
    
    # Ejecutar servidor
    uvicorn.run(app, host="0.0.0.0", port=5000, log_level="info")
