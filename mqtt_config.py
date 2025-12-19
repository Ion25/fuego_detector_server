"""
Configuración MQTT con HiveMQ Cloud
Universidad Nacional de San Agustín - Arequipa, Perú

Este módulo maneja la conexión MQTT entre el Arduino (red Redmi 9)
y el servidor Python (red honor) usando HiveMQ como broker en la nube.
"""

import json
import paho.mqtt.client as mqtt
from datetime import datetime

# ============================================================================
# CONFIGURACIÓN HIVEMQ CLOUD (Broker público gratuito)
# ============================================================================
MQTT_BROKER = "broker.hivemq.com"  # Broker público de HiveMQ
MQTT_PORT = 1883
MQTT_KEEPALIVE = 60

# Topics MQTT
MQTT_TOPIC_SENSORES = "unsa/fire_detection/sensores"
MQTT_TOPIC_COMANDO = "unsa/fire_detection/comando"
MQTT_TOPIC_STATUS = "unsa/fire_detection/status"

# Topics para cámara Android
MQTT_TOPIC_COMANDO_CAMARA = "unsa/fire_detection/comando_camara"
MQTT_TOPIC_FOTO = "unsa/fire_detection/foto"
MQTT_TOPIC_AUDIO = "unsa/fire_detection/audio"
MQTT_TOPIC_STATUS_CAMARA = "unsa/fire_detection/status_camara"

# Cliente MQTT global
mqtt_client = None

# Variables para reconstruir foto/audio desde chunks
foto_chunks_buffer = {}
audio_chunks_buffer = {}

# ============================================================================
# CALLBACKS MQTT
# ============================================================================

def on_connect(client, userdata, flags, rc):
    """Callback cuando se conecta al broker MQTT"""
    if rc == 0:
        print(f"✓ Conectado al broker MQTT: {MQTT_BROKER}")
        
        # Suscribirse a topics de Arduino
        client.subscribe(MQTT_TOPIC_SENSORES, qos=1)
        client.subscribe(MQTT_TOPIC_STATUS, qos=1)
        print(f"✓ Suscrito a: {MQTT_TOPIC_SENSORES}")
        print(f"✓ Suscrito a: {MQTT_TOPIC_STATUS}")
        
        # Suscribirse a topics de cámara Android
        client.subscribe(MQTT_TOPIC_FOTO, qos=1)
        client.subscribe(MQTT_TOPIC_AUDIO, qos=1)
        client.subscribe(MQTT_TOPIC_STATUS_CAMARA, qos=1)
        print(f"✓ Suscrito a: {MQTT_TOPIC_FOTO}")
        print(f"✓ Suscrito a: {MQTT_TOPIC_AUDIO}")
        print(f"✓ Suscrito a: {MQTT_TOPIC_STATUS_CAMARA}")
    else:
        print(f"✗ Error de conexión MQTT. Código: {rc}")

def on_disconnect(client, userdata, rc):
    """Callback cuando se desconecta del broker"""
    if rc != 0:
        print(f"⚠️  Desconexión inesperada del broker MQTT. Código: {rc}")
        print("   Intentando reconectar...")

def on_message(client, userdata, msg):
    """Callback cuando llega un mensaje MQTT"""
    try:
        topic = msg.topic
        payload = msg.payload.decode('utf-8')
        
        print(f"\n📩 Mensaje MQTT recibido:")
        print(f"   Topic: {topic}")
        print(f"   Payload: {payload[:100]}...")  # Primeros 100 caracteres
        
        # Procesar según el topic
        if topic == MQTT_TOPIC_SENSORES:
            # Es un mensaje de datos de sensores
            data = json.loads(payload)
            print(f"   🌡️  Temperatura: {data.get('temperatura')}°C")
            print(f"   💡 Luz: {data.get('luz')} lux")
            
            # Aquí puedes llamar a tu función para procesar los datos
            # Por ejemplo: procesar_datos_sensores(data)
            
        elif topic == MQTT_TOPIC_STATUS:
            print(f"   ℹ️  Status del Arduino: {payload}")
            
    except Exception as e:
        print(f"✗ Error procesando mensaje MQTT: {e}")

# ============================================================================
# FUNCIONES PRINCIPALES
# ============================================================================

def inicializar_mqtt():
    """Inicializa la conexión MQTT"""
    global mqtt_client
    
    try:
        # Crear cliente MQTT
        client_id = f"unsa_fire_server_{datetime.now().strftime('%Y%m%d%H%M%S')}"
        mqtt_client = mqtt.Client(client_id=client_id)
        
        # Configurar callbacks
        mqtt_client.on_connect = on_connect
        mqtt_client.on_disconnect = on_disconnect
        mqtt_client.on_message = on_message_with_callback
        
        # Conectar al broker
        print(f"\n🔌 Conectando a MQTT broker: {MQTT_BROKER}:{MQTT_PORT}")
        mqtt_client.connect(MQTT_BROKER, MQTT_PORT, MQTT_KEEPALIVE)
        
        # Iniciar loop en segundo plano
        mqtt_client.loop_start()
        
        return mqtt_client
        
    except Exception as e:
        print(f"✗ Error al inicializar MQTT: {e}")
        return None

def publicar_comando(comando):
    """Publica un comando al Arduino vía MQTT"""
    if mqtt_client and mqtt_client.is_connected():
        try:
            mqtt_client.publish(MQTT_TOPIC_COMANDO, comando)
            print(f"✓ Comando publicado: {comando}")
            return True
        except Exception as e:
            print(f"✗ Error al publicar comando: {e}")
            return False
    else:
        print("✗ Cliente MQTT no conectado")
        return False

def solicitar_captura_mqtt():
    """
    Solicita captura a la cámara Android vía MQTT.
    Funciona incluso si están en diferentes redes WiFi.
    """
    if mqtt_client and mqtt_client.is_connected():
        try:
            comando = json.dumps({
                "accion": "CAPTURAR",
                "timestamp": datetime.now().isoformat()
            })
            mqtt_client.publish(MQTT_TOPIC_COMANDO_CAMARA, comando, qos=1)
            print(f"✓ Comando de captura enviado a cámara vía MQTT")
            return True
        except Exception as e:
            print(f"✗ Error al solicitar captura por MQTT: {e}")
            return False
    else:
        print("✗ Cliente MQTT no conectado")
        return False

def reconstruir_desde_chunks(chunks_dict):
    """Reconstruye datos base64 desde múltiples chunks"""
    try:
        # Ordenar chunks por chunk_id
        chunks_ordenados = sorted(chunks_dict.items())
        # Concatenar todos los datos
        data_completo = ''.join([chunk['data'] for _, chunk in chunks_ordenados])
        return data_completo
    except Exception as e:
        print(f"✗ Error al reconstruir chunks: {e}")
        return None

def verificar_multimedia_completa(timestamp, foto_base64):
    """
    Verifica si tenemos foto + audio completos y llama al callback
    """
    global audio_chunks_buffer
    
    try:
        # Verificar si hay audio para este timestamp
        audio_base64 = None
        if timestamp in audio_chunks_buffer:
            print(f"   ✓ Audio también disponible")
            audio_base64 = reconstruir_desde_chunks(audio_chunks_buffer[timestamp])
            del audio_chunks_buffer[timestamp]
        
        # Llamar al callback con los datos completos
        if callback_multimedia_completa and foto_base64:
            print(f"\n📤 Procesando multimedia completa...")
            callback_multimedia_completa({
                "imagen": foto_base64,
                "audio": audio_base64,
                "timestamp": timestamp,
                "dispositivo": "camara_mqtt_android"
            })
        
    except Exception as e:
        print(f"✗ Error al verificar multimedia: {e}")

def detener_mqtt():
    """Detiene la conexión MQTT"""
    global mqtt_client
    if mqtt_client:
        mqtt_client.loop_stop()
        mqtt_client.disconnect()
        print("✓ Conexión MQTT cerrada")

# ============================================================================
# CALLBACK PERSONALIZADO PARA INTEGRAR CON server.py
# ============================================================================

# Variable para almacenar el callback personalizado
callback_datos_sensores = None
callback_multimedia_completa = None

def set_callback_sensores(callback):
    """
    Configura un callback que se llamará cuando lleguen datos de sensores.
    
    El callback debe aceptar un diccionario con los datos:
    {
        "temperatura": float,
        "luz": float,
        "humedad": float,
        "presion": float
    }
    """
    global callback_datos_sensores
    callback_datos_sensores = callback
    print("✓ Callback de sensores configurado")

def set_callback_multimedia(callback):
    """
    Configura un callback que se llamará cuando se complete la recepción
    de foto + audio desde la cámara Android.
    
    El callback debe aceptar:
    {
        "foto_base64": str,
        "audio_base64": str or None,
        "timestamp": str
    }
    """
    global callback_multimedia_completa
    callback_multimedia_completa = callback
    print("✓ Callback de multimedia configurado")

def procesar_datos_mqtt(topic, data):
    """Procesa los datos recibidos por MQTT y llama al callback"""
    if topic == MQTT_TOPIC_SENSORES and callback_datos_sensores:
        try:
            callback_datos_sensores(data)
        except Exception as e:
            print(f"✗ Error en callback de sensores: {e}")
    elif topic in [MQTT_TOPIC_FOTO, MQTT_TOPIC_AUDIO] and callback_multimedia_completa:
        try:
            # Aquí asumimos que 'data' contiene el diccionario completo con foto y audio
            callback_multimedia_completa(data)
        except Exception as e:
            print(f"✗ Error en callback de multimedia: {e}")

# Modificar on_message para usar el callback
def on_message_with_callback(client, userdata, msg):
    """Callback mejorado que usa el callback personalizado"""
    global foto_chunks_buffer, audio_chunks_buffer
    
    try:
        topic = msg.topic
        payload = msg.payload.decode('utf-8')
        
        print(f"\n📩 Mensaje MQTT recibido:")
        print(f"   Topic: {topic}")
        
        if topic == MQTT_TOPIC_SENSORES:
            data = json.loads(payload)
            print(f"   🌡️  Temperatura: {data.get('temperatura')}°C")
            print(f"   💡 Luz: {data.get('luz')} lux")
            
            # Llamar al callback si está configurado
            if callback_datos_sensores:
                callback_datos_sensores(data)
            
        elif topic == MQTT_TOPIC_STATUS:
            print(f"   ℹ️  Status: {payload}")
            
        elif topic == MQTT_TOPIC_STATUS_CAMARA:
            print(f"   📷 Status cámara: {payload}")
            
        elif topic == MQTT_TOPIC_FOTO:
            # Mensaje con chunk de foto
            data = json.loads(payload)
            chunk_id = data.get('chunk_id')
            total_chunks = data.get('total_chunks')
            timestamp = data.get('timestamp')
            
            print(f"   📷 Foto chunk {chunk_id+1}/{total_chunks}")
            
            # Guardar chunk
            if timestamp not in foto_chunks_buffer:
                foto_chunks_buffer[timestamp] = {}
            
            foto_chunks_buffer[timestamp][chunk_id] = data
            
            # Verificar si tenemos todos los chunks
            if len(foto_chunks_buffer[timestamp]) == total_chunks:
                print(f"   ✓ Todos los chunks de foto recibidos")
                
                # Reconstruir foto completa
                foto_base64 = reconstruir_desde_chunks(foto_chunks_buffer[timestamp])
                
                # Limpiar buffer
                del foto_chunks_buffer[timestamp]
                
                # Verificar si también tenemos audio
                # (dar tiempo para que llegue el audio)
                import threading
                threading.Timer(
                    2.0,
                    verificar_multimedia_completa,
                    args=(timestamp, foto_base64)
                ).start()
        
        elif topic == MQTT_TOPIC_AUDIO:
            # Mensaje con chunk de audio
            data = json.loads(payload)
            chunk_id = data.get('chunk_id')
            total_chunks = data.get('total_chunks')
            timestamp = data.get('timestamp')
            
            print(f"   🎤 Audio chunk {chunk_id+1}/{total_chunks}")
            
            # Guardar chunk
            if timestamp not in audio_chunks_buffer:
                audio_chunks_buffer[timestamp] = {}
            
            audio_chunks_buffer[timestamp][chunk_id] = data
            
            # Verificar si tenemos todos los chunks
            if len(audio_chunks_buffer[timestamp]) == total_chunks:
                print(f"   ✓ Todos los chunks de audio recibidos")
            # Aquí podrías agregar código para manejar la foto recibida
            
        elif topic == MQTT_TOPIC_AUDIO:
            # Mensaje con audio
            print("   🎵 Audio recibido")
            # Aquí podrías agregar código para manejar el audio recibido
            
    except Exception as e:
        print(f"✗ Error procesando mensaje MQTT: {e}")

# ============================================================================
# MAIN - Para pruebas
# ============================================================================
if __name__ == "__main__":
    print("=" * 60)
    print("MQTT Client Test - UNSA Fire Detection")
    print("=" * 60)
    
    # Inicializar MQTT
    client = inicializar_mqtt()
    
    if client:
        print("\n✓ Cliente MQTT iniciado")
        print("  Esperando mensajes del Arduino...")
        print("  Presiona Ctrl+C para salir\n")
        
        try:
            # Mantener el programa corriendo
            import time
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            print("\n\n⏹️  Deteniendo cliente MQTT...")
            detener_mqtt()
            print("✓ Programa terminado")
    else:
        print("\n✗ No se pudo inicializar el cliente MQTT")
