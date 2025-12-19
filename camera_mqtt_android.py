"""
Cliente de Cámara Automática con MQTT para Teléfono Android
Universidad Nacional de San Agustín - Arequipa, Perú

Este script debe ejecutarse en TERMUX en el teléfono Android.
Usa MQTT (HiveMQ) para comunicación, permitiendo que la cámara
y el servidor estén en DIFERENTES REDES WiFi.

INSTALACIÓN EN TERMUX:
1. Instalar Termux desde F-Droid
2. pkg update && pkg upgrade
3. pkg install python termux-api
4. pip install paho-mqtt requests pillow
5. Dar permisos de cámara y micrófono a Termux:API

EJECUCIÓN:
python3 camera_mqtt_android.py
"""

import paho.mqtt.client as mqtt
import subprocess
import os
import time
import requests
from datetime import datetime
import base64
import json

# ============================================================================
# CONFIGURACIÓN MQTT
# ============================================================================

# Broker MQTT (mismo que usa el Arduino y el servidor)
MQTT_BROKER = "broker.hivemq.com"
MQTT_PORT = 1883
MQTT_KEEPALIVE = 60

# Topics MQTT
MQTT_TOPIC_COMANDO_CAMARA = "unsa/fire_detection/comando_camara"  # Recibe comandos
MQTT_TOPIC_FOTO = "unsa/fire_detection/foto"  # Envía foto
MQTT_TOPIC_AUDIO = "unsa/fire_detection/audio"  # Envía audio
MQTT_TOPIC_VIDEO = "unsa/fire_detection/video"  # Envía video
MQTT_TOPIC_STATUS_CAMARA = "unsa/fire_detection/status_camara"  # Estado de la cámara

# Configuración de captura
CAMARA_ID = 0  # 0=trasera, 1=frontal

# Modo de captura: secuencia de fotos
CAPTURAR_SECUENCIA = True  # ✅ Captura múltiples fotos en intervalos
NUMERO_FOTOS = 5  # Número de fotos a capturar
INTERVALO_FOTOS = 2  # Segundos entre cada foto

# Modos alternativos (desactivados)
CAPTURAR_AUDIO = False  # ❌ Audio no funciona en este dispositivo
CAPTURAR_VIDEO = False  # ❌ termux-camera-video no disponible

# Directorio para archivos temporales
TEMP_DIR = "/data/data/com.termux/files/home/fire_detection_temp"

# Cliente MQTT global
mqtt_client = None

# ============================================================================
# INICIALIZACIÓN
# ============================================================================

# Crear directorio temporal si no existe
os.makedirs(TEMP_DIR, exist_ok=True)

print("=" * 60)
print("🎥 Cámara Automática MQTT - UNSA Fire Detection")
print("=" * 60)
print(f"📁 Directorio temporal: {TEMP_DIR}")
print(f"🌐 Broker MQTT: {MQTT_BROKER}:{MQTT_PORT}")
print(f"📡 Topic de comandos: {MQTT_TOPIC_COMANDO_CAMARA}")
print()

# ============================================================================
# FUNCIONES DE CAPTURA
# ============================================================================

def capturar_foto():
    """Captura una foto usando termux-camera-photo"""
    try:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        foto_path = os.path.join(TEMP_DIR, f"captura_{timestamp}.jpg")
        
        print(f"📸 Capturando foto...")
        
        result = subprocess.run(
            ["termux-camera-photo", "-c", str(CAMARA_ID), foto_path],
            capture_output=True,
            text=True,
            timeout=10
        )
        
        if result.returncode == 0 and os.path.exists(foto_path):
            size = os.path.getsize(foto_path)
            print(f"✓ Foto capturada: {size} bytes")
            return foto_path
        else:
            print(f"✗ Error al capturar foto: {result.stderr}")
            return None
            
    except Exception as e:
        print(f"✗ Excepción al capturar foto: {e}")
        return None

def probar_formatos_audio(duracion=3):
    """
    Prueba diferentes formatos de audio para encontrar uno que funcione.
    Retorna el formato que mejor funciona.
    """
    formatos = [
        ("m4a", None),           # M4A sin encoder específico (por defecto)
        ("aac", "aac"),          # AAC explícito
        ("3gp", "amr_nb"),       # AMR Narrowband (común en Android)
        ("mp3", None),           # MP3 sin encoder
        ("wav", "wav"),          # WAV
    ]
    
    print(f"🔍 Probando formatos de audio disponibles...")
    
    for extension, encoder in formatos:
        try:
            test_path = os.path.join(TEMP_DIR, f"test_audio.{extension}")
            
            # Construir comando
            cmd = ["termux-microphone-record", "-f", test_path, "-l", str(duracion)]
            if encoder:
                cmd.extend(["-e", encoder])
            
            print(f"   Probando {extension.upper()} {'con encoder ' + encoder if encoder else '(por defecto)'}...", end=" ")
            
            # Lanzar grabación
            subprocess.run(cmd, capture_output=True, timeout=2)
            
            # Esperar a que termine
            time.sleep(duracion + 2)
            
            # Verificar resultado
            if os.path.exists(test_path):
                size = os.path.getsize(test_path)
                if size > 50000:  # Al menos 50KB = tiene audio real
                    print(f"✅ FUNCIONA ({size} bytes)")
                    # Limpiar archivo de prueba
                    os.remove(test_path)
                    return (extension, encoder)
                else:
                    print(f"❌ Muy pequeño ({size} bytes)")
                    os.remove(test_path)
            else:
                print(f"❌ No se creó")
        
        except Exception as e:
            print(f"❌ Error: {e}")
    
    print(f"⚠️  Ningún formato funcionó correctamente")
    return None

def grabar_audio(duracion=5):
    """
    Graba audio durante X segundos.
    Ahora detecta automáticamente el mejor formato disponible.
    
    IMPORTANTE: termux-microphone-record es ASÍNCRONO
    - El comando retorna inmediatamente
    - La grabación continúa en background
    - El archivo se llena progresivamente
    - Debemos esperar manualmente a que termine
    """
    try:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Intentar con M4A primero (más compatible)
        extension = "m4a"
        encoder = None
        audio_path = os.path.join(TEMP_DIR, f"audio_{timestamp}.{extension}")
        
        print(f"🎤 Iniciando grabación de audio ({duracion} segundos)...")
        print(f"   Formato: {extension.upper()}")
        
        # Construir comando
        cmd = ["termux-microphone-record", "-f", audio_path, "-l", str(duracion)]
        if encoder:
            cmd.extend(["-e", encoder])
        
        # Lanzar comando (retorna inmediatamente, pero la grabación continúa)
        result = subprocess.run(
            cmd,
            capture_output=True,
            timeout=3  # Solo esperamos que el comando se lance
        )
        
        # El comando ya se lanzó, ahora DEBEMOS ESPERAR a que termine la grabación
        print(f"   ⏱️  Grabación en progreso... esperando {duracion} segundos")
        print(f"   💡 El icono de micrófono debe estar activo ahora")
        
        # Esperar la duración completa + margen de seguridad
        time.sleep(duracion + 2)
        
        print(f"   ⏹️  Grabación completada, verificando archivo...")
        
        # Ahora sí verificar el archivo
        if os.path.exists(audio_path):
            # Esperar un poco más por si aún se está escribiendo
            time.sleep(1)
            
            size = os.path.getsize(audio_path)
            print(f"✓ Audio grabado: {size} bytes (~{size/1024:.1f} KB)")
            
            if size < 50000:  # Menos de 50KB es sospechoso para 5 segundos
                print(f"   ⚠️  Archivo muy pequeño, puede estar corrupto")
                print(f"   💡 Ejecuta en Termux: python3 -c 'from camera_mqtt_android import probar_formatos_audio; probar_formatos_audio()'")
                # Aún así retornamos el archivo por si sirve
            
            return audio_path
        else:
            print(f"✗ No se pudo crear el archivo de audio")
            return None
            
    except subprocess.TimeoutExpired:
        print(f"⚠️  Timeout al lanzar comando, pero puede estar grabando...")
        # Intentar esperar de todas formas
        time.sleep(duracion + 2)
        if os.path.exists(audio_path):
            size = os.path.getsize(audio_path)
            print(f"✓ Audio grabado (con timeout): {size} bytes")
            return audio_path
        return None
    except Exception as e:
        print(f"✗ Excepción al grabar audio: {e}")
        return None

def grabar_video(duracion=5):
    """
    Graba un video durante X segundos usando termux-camera-video
    
    NOTA: termux-camera-video puede NO estar disponible en todas las versiones.
    Si no existe, intenta actualizar: pkg upgrade termux-api
    """
    try:
        # Primero verificar si el comando existe
        result_check = subprocess.run(
            ["which", "termux-camera-video"],
            capture_output=True,
            text=True
        )
        
        if result_check.returncode != 0:
            print(f"❌ termux-camera-video no está disponible en este dispositivo")
            print(f"   Intenta: pkg upgrade termux-api")
            return None
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        video_path = os.path.join(TEMP_DIR, f"video_{timestamp}.mp4")
        
        print(f"🎥 Grabando video ({duracion} segundos)...")
        print(f"   Comando: termux-camera-video -c {CAMARA_ID} -s 1280x720 {video_path}")
        
        # Iniciar grabación en background
        proceso = subprocess.Popen(
            ["termux-camera-video", 
             "-c", str(CAMARA_ID),
             "-s", "1280x720",  # HD 720p (balance entre calidad y tamaño)
             video_path],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        
        # Esperar la duración especificada
        print(f"   ⏱️  Grabando... (esperando {duracion} segundos)")
        time.sleep(duracion)
        
        # Detener la grabación enviando SIGTERM
        print(f"   ⏹️  Deteniendo grabación...")
        proceso.terminate()
        try:
            proceso.wait(timeout=3)
        except subprocess.TimeoutExpired:
            print(f"   ⚠️  Forzando cierre...")
            proceso.kill()
            proceso.wait()
        
        # Dar tiempo para que se escriba el archivo
        time.sleep(0.5)
        
        # Verificar que el archivo existe y tiene contenido
        if os.path.exists(video_path):
            size = os.path.getsize(video_path)
            if size > 50000:  # Al menos 50KB para considerar válido
                print(f"✓ Video grabado: {size} bytes (~{size/1024/1024:.1f} MB)")
                return video_path
            else:
                print(f"✗ Video demasiado pequeño ({size} bytes), probablemente error")
                return None
        else:
            print(f"✗ No se pudo crear el archivo de video")
            return None
            
    except Exception as e:
        print(f"✗ Excepción al grabar video: {e}")
        return None

def capturar_secuencia_fotos(cantidad=5, intervalo=1):
    """
    Alternativa al video: Captura una secuencia rápida de fotos.
    Útil cuando termux-camera-video no está disponible.
    """
    try:
        fotos = []
        timestamp_base = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        print(f"📸 Capturando secuencia de {cantidad} fotos...")
        
        for i in range(cantidad):
            foto_path = os.path.join(TEMP_DIR, f"secuencia_{timestamp_base}_{i+1:02d}.jpg")
            
            print(f"   Foto {i+1}/{cantidad}...")
            
            result = subprocess.run(
                ["termux-camera-photo", "-c", str(CAMARA_ID), foto_path],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode == 0 and os.path.exists(foto_path):
                size = os.path.getsize(foto_path)
                print(f"   ✓ {size} bytes")
                fotos.append(foto_path)
            else:
                print(f"   ✗ Error en foto {i+1}")
            
            # Esperar antes de la siguiente (excepto la última)
            if i < cantidad - 1:
                time.sleep(intervalo)
        
        if fotos:
            print(f"✓ Secuencia capturada: {len(fotos)} fotos")
            return fotos
        else:
            print(f"✗ No se pudo capturar ninguna foto de la secuencia")
            return None
            
    except Exception as e:
        print(f"✗ Excepción al capturar secuencia: {e}")
        return None

def convertir_a_base64(filepath):
    """Convierte un archivo a base64"""
    try:
        with open(filepath, 'rb') as f:
            return base64.b64encode(f.read()).decode('utf-8')
    except Exception as e:
        print(f"✗ Error al convertir a base64: {e}")
        return None

def dividir_base64(data, chunk_size=50000):
    """Divide base64 en chunks para MQTT (límite de mensaje)"""
    return [data[i:i+chunk_size] for i in range(0, len(data), chunk_size)]

# ============================================================================
# FUNCIONES MQTT
# ============================================================================

def enviar_por_mqtt(foto_path, audio_path, video_path=None):
    """
    Envía foto/video y audio por MQTT al servidor.
    Divide en chunks si es necesario.
    """
    try:
        print(f"\n📤 Preparando envío por MQTT...")
        
        # Convertir a base64
        foto_base64 = convertir_a_base64(foto_path) if foto_path else None
        audio_base64 = convertir_a_base64(audio_path) if audio_path else None
        video_base64 = convertir_a_base64(video_path) if video_path else None
        
        if not foto_base64 and not video_base64:
            print("✗ No hay foto ni video para enviar")
            return False
        
        # Preparar metadata
        metadata = {
            "timestamp": datetime.now().isoformat(),
            "dispositivo": "camara_mqtt_android",
            "tiene_audio": audio_base64 is not None,
            "tiene_video": video_base64 is not None,
            "tipo": "video" if video_base64 else "foto"
        }
        
        # Enviar metadata primero
        topic_base = MQTT_TOPIC_VIDEO if video_base64 else MQTT_TOPIC_FOTO
        mqtt_client.publish(
            f"{topic_base}/metadata",
            json.dumps(metadata),
            qos=1
        )
        print(f"✓ Metadata enviada")
        
        # Enviar video o foto (puede dividirse en chunks)
        if video_base64:
            # Enviar video
            video_chunks = dividir_base64(video_base64)
            total_chunks = len(video_chunks)
            
            print(f"📡 Enviando video en {total_chunks} chunk(s)...")
            
            for i, chunk in enumerate(video_chunks):
                payload = {
                    "chunk_id": i,
                    "total_chunks": total_chunks,
                    "data": chunk,
                    "timestamp": metadata["timestamp"]
                }
                
                mqtt_client.publish(
                    MQTT_TOPIC_VIDEO,
                    json.dumps(payload),
                    qos=1
                )
                
                print(f"  Chunk {i+1}/{total_chunks} enviado")
                time.sleep(0.1)  # Pequeña pausa entre chunks
        else:
            # Enviar foto
            foto_chunks = dividir_base64(foto_base64)
            total_chunks = len(foto_chunks)
            
            print(f"📡 Enviando foto en {total_chunks} chunk(s)...")
            
            for i, chunk in enumerate(foto_chunks):
                payload = {
                    "chunk_id": i,
                    "total_chunks": total_chunks,
                    "data": chunk,
                    "timestamp": metadata["timestamp"]
                }
                
                mqtt_client.publish(
                    MQTT_TOPIC_FOTO,
                    json.dumps(payload),
                    qos=1
                )
                
                print(f"  Chunk {i+1}/{total_chunks} enviado")
                time.sleep(0.1)  # Pequeña pausa entre chunks
        
        # Enviar audio si existe
        if audio_base64:
            audio_chunks = dividir_base64(audio_base64)
            total_audio_chunks = len(audio_chunks)
            
            print(f"📡 Enviando audio en {total_audio_chunks} chunk(s)...")
            
            for i, chunk in enumerate(audio_chunks):
                payload = {
                    "chunk_id": i,
                    "total_chunks": total_audio_chunks,
                    "data": chunk,
                    "timestamp": metadata["timestamp"]
                }
                
                mqtt_client.publish(
                    MQTT_TOPIC_AUDIO,
                    json.dumps(payload),
                    qos=1
                )
                
                print(f"  Chunk {i+1}/{total_audio_chunks} enviado")
                time.sleep(0.1)
        
        print(f"✅ Datos enviados por MQTT exitosamente")
        return True
        
    except Exception as e:
        print(f"✗ Error al enviar por MQTT: {e}")
        return False
    finally:
        # Limpiar archivos temporales
        try:
            if foto_path and os.path.exists(foto_path):
                os.remove(foto_path)
                print(f"🗑️  Foto temporal eliminada")
            if audio_path and os.path.exists(audio_path):
                os.remove(audio_path)
                print(f"🗑️  Audio temporal eliminado")
            if video_path and os.path.exists(video_path):
                os.remove(video_path)
                print(f"🗑️  Video temporal eliminado")
        except Exception as e:
            print(f"⚠️  Error al limpiar temporales: {e}")

def procesar_comando_captura():
    """
    Procesa el comando de captura automáticamente.
    Captura una o varias fotos según configuración y las envía por MQTT.
    """
    print("\n" + "=" * 60)
    print("🚨 COMANDO DE CAPTURA RECIBIDO VÍA MQTT")
    print("=" * 60)
    
    try:
        fotos_paths = []
        
        # Capturar fotos según configuración
        if CAPTURAR_SECUENCIA:
            # Capturar secuencia de fotos
            print(f"\n📸 Capturando secuencia de {NUMERO_FOTOS} fotos...")
            print(f"   Intervalo: {INTERVALO_FOTOS} segundos entre fotos")
            
            for i in range(NUMERO_FOTOS):
                print(f"\n📷 Foto {i+1}/{NUMERO_FOTOS}:")
                foto_path = capturar_foto()
                
                if foto_path:
                    fotos_paths.append(foto_path)
                    print(f"✓ Foto {i+1} capturada")
                else:
                    print(f"✗ Error en foto {i+1}")
                
                # Esperar antes de siguiente foto (excepto la última)
                if i < NUMERO_FOTOS - 1:
                    print(f"⏳ Esperando {INTERVALO_FOTOS} segundos...")
                    time.sleep(INTERVALO_FOTOS)
            
            print(f"\n✅ Secuencia completada: {len(fotos_paths)}/{NUMERO_FOTOS} fotos capturadas")
        else:
            # Capturar solo una foto
            print(f"\n📸 Capturando foto única...")
            foto_path = capturar_foto()
            if foto_path:
                fotos_paths.append(foto_path)
        
        # Verificar que tenemos al menos una foto
        if not fotos_paths:
            print("✗ No se pudo capturar ninguna foto")
            mqtt_client.publish(
                MQTT_TOPIC_STATUS_CAMARA,
                json.dumps({"status": "error", "mensaje": "Error al capturar fotos"}),
                qos=1
            )
            return False
        
        # Enviar todas las fotos por MQTT
        print(f"\n📤 Enviando {len(fotos_paths)} foto(s) por MQTT...")
        
        exito_total = True
        for i, foto_path in enumerate(fotos_paths, 1):
            print(f"\n📡 Enviando foto {i}/{len(fotos_paths)}...")
            exito = enviar_por_mqtt(foto_path, None, None)  # Solo foto, sin audio ni video
            if not exito:
                exito_total = False
                print(f"⚠️  Error enviando foto {i}")
        
        if exito_total:
            print("\n✅ Todas las fotos enviadas exitosamente")
            mqtt_client.publish(
                MQTT_TOPIC_STATUS_CAMARA,
                json.dumps({
                    "status": "success",
                    "mensaje": f"{len(fotos_paths)} foto(s) capturada(s) y enviada(s)",
                    "timestamp": datetime.now().isoformat(),
                    "cantidad_fotos": len(fotos_paths)
                }),
                qos=1
            )
            return True
        else:
            print("\n⚠️  Algunas fotos no se pudieron enviar")
            return False
            
    except Exception as e:
        print(f"\n✗ Error en proceso de captura: {e}")
        mqtt_client.publish(
            MQTT_TOPIC_STATUS_CAMARA,
            json.dumps({"status": "error", "mensaje": str(e)}),
            qos=1
        )
        return False

# ============================================================================
# CALLBACKS MQTT
# ============================================================================

def on_connect(client, userdata, flags, rc):
    """Callback cuando se conecta al broker MQTT"""
    if rc == 0:
        print(f"\n✓ Conectado al broker MQTT: {MQTT_BROKER}")
        
        # Suscribirse al topic de comandos
        client.subscribe(MQTT_TOPIC_COMANDO_CAMARA, qos=1)
        print(f"✓ Suscrito a: {MQTT_TOPIC_COMANDO_CAMARA}")
        
        # Publicar estado inicial
        client.publish(
            MQTT_TOPIC_STATUS_CAMARA,
            json.dumps({
                "status": "online",
                "dispositivo": "camara_mqtt_android",
                "timestamp": datetime.now().isoformat()
            }),
            qos=1
        )
        print(f"✓ Estado publicado en: {MQTT_TOPIC_STATUS_CAMARA}")
        print(f"\n🎥 Cámara lista. Esperando comandos...")
        
    else:
        print(f"✗ Error de conexión MQTT. Código: {rc}")

def on_disconnect(client, userdata, rc):
    """Callback cuando se desconecta del broker"""
    if rc != 0:
        print(f"\n⚠️  Desconexión inesperada del broker MQTT. Código: {rc}")
        print("   Intentando reconectar...")

def on_message(client, userdata, msg):
    """Callback cuando llega un mensaje MQTT"""
    try:
        topic = msg.topic
        payload = msg.payload.decode('utf-8')
        
        print(f"\n📩 Mensaje MQTT recibido:")
        print(f"   Topic: {topic}")
        print(f"   Payload: {payload[:100]}")
        
        if topic == MQTT_TOPIC_COMANDO_CAMARA:
            # Parsear comando
            try:
                comando = json.loads(payload)
                accion = comando.get("accion", "")
                
                if accion == "CAPTURAR":
                    print(f"   Acción: CAPTURAR")
                    # Procesar captura en un hilo separado para no bloquear
                    import threading
                    thread = threading.Thread(target=procesar_comando_captura)
                    thread.daemon = True
                    thread.start()
                    
                elif accion == "PING":
                    print(f"   Acción: PING")
                    # Responder con pong
                    mqtt_client.publish(
                        MQTT_TOPIC_STATUS_CAMARA,
                        json.dumps({
                            "status": "pong",
                            "timestamp": datetime.now().isoformat()
                        }),
                        qos=1
                    )
                    
            except json.JSONDecodeError:
                # Si no es JSON, asumir comando simple
                if payload.upper() == "CAPTURAR":
                    import threading
                    thread = threading.Thread(target=procesar_comando_captura)
                    thread.daemon = True
                    thread.start()
            
    except Exception as e:
        print(f"✗ Error procesando mensaje MQTT: {e}")

# ============================================================================
# MAIN
# ============================================================================

def inicializar_mqtt():
    """Inicializa la conexión MQTT"""
    global mqtt_client
    
    try:
        # Crear cliente MQTT
        client_id = f"unsa_camera_{datetime.now().strftime('%Y%m%d%H%M%S')}"
        mqtt_client = mqtt.Client(client_id=client_id)
        
        # Configurar callbacks
        mqtt_client.on_connect = on_connect
        mqtt_client.on_disconnect = on_disconnect
        mqtt_client.on_message = on_message
        
        # Conectar al broker
        print(f"🔌 Conectando a MQTT broker: {MQTT_BROKER}:{MQTT_PORT}...")
        mqtt_client.connect(MQTT_BROKER, MQTT_PORT, MQTT_KEEPALIVE)
        
        # Iniciar loop
        mqtt_client.loop_start()
        
        return True
        
    except Exception as e:
        print(f"✗ Error al inicializar MQTT: {e}")
        return False

if __name__ == '__main__':
    print("\n🚀 Iniciando cámara automática con MQTT...")
    print(f"📱 Asegúrate de que Termux:API tenga permisos de cámara y micrófono")
    print(f"💡 Para detener: Ctrl+C\n")
    
    if inicializar_mqtt():
        print("\n✅ Sistema iniciado correctamente")
        print("=" * 60 + "\n")
        
        try:
            # Mantener el programa corriendo
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            print("\n\n⏹️  Deteniendo cámara...")
            
            # Publicar estado offline
            if mqtt_client:
                mqtt_client.publish(
                    MQTT_TOPIC_STATUS_CAMARA,
                    json.dumps({
                        "status": "offline",
                        "timestamp": datetime.now().isoformat()
                    }),
                    qos=1
                )
                mqtt_client.loop_stop()
                mqtt_client.disconnect()
            
            print("✓ Cámara detenida")
    else:
        print("\n✗ No se pudo inicializar el sistema MQTT")
