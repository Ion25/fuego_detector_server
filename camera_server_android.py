"""
Cliente de Cámara Automática para Teléfono Android
Universidad Nacional de San Agustín - Arequipa, Perú

Este script debe ejecutarse en TERMUX en el teléfono Android.
Crea un servidor HTTP que recibe comandos del servidor principal
y automáticamente captura foto + audio cuando detecta peligro.

INSTALACIÓN EN TERMUX:
1. Instalar Termux desde F-Droid
2. pkg update && pkg upgrade
3. pkg install python termux-api
4. pip install flask requests pillow
5. Dar permisos de cámara y micrófono a Termux:API

EJECUCIÓN:
python3 camera_server_android.py
"""

from flask import Flask, request, jsonify
import subprocess
import os
import time
import requests
from datetime import datetime
import base64

# ============================================================================
# CONFIGURACIÓN
# ============================================================================

# IP del servidor principal (tu PC con el servidor FastAPI)
SERVIDOR_PRINCIPAL = "http://10.166.236.39:5000"  # Cambiar a la IP actual

# Puerto donde correrá este servidor en el teléfono
PUERTO_CAMARA = 8080

# Directorio para archivos temporales
TEMP_DIR = "/data/data/com.termux/files/home/fire_detection_temp"

# ============================================================================
# INICIALIZACIÓN
# ============================================================================

app = Flask(__name__)

# Crear directorio temporal si no existe
os.makedirs(TEMP_DIR, exist_ok=True)

print("=" * 60)
print("🎥 Servidor de Cámara Automática - UNSA Fire Detection")
print("=" * 60)
print(f"📁 Directorio temporal: {TEMP_DIR}")
print(f"🌐 Servidor principal: {SERVIDOR_PRINCIPAL}")
print()

# ============================================================================
# FUNCIONES DE CAPTURA
# ============================================================================

def capturar_foto():
    """
    Captura una foto usando termux-camera-photo
    Retorna la ruta del archivo o None si falla
    """
    try:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        foto_path = os.path.join(TEMP_DIR, f"captura_{timestamp}.jpg")
        
        print(f"📸 Capturando foto...")
        
        # Usar cámara trasera (0) o frontal (1)
        # termux-camera-photo -c 0 archivo.jpg
        result = subprocess.run(
            ["termux-camera-photo", "-c", "0", foto_path],
            capture_output=True,
            text=True,
            timeout=10
        )
        
        if result.returncode == 0 and os.path.exists(foto_path):
            size = os.path.getsize(foto_path)
            print(f"✓ Foto capturada: {foto_path} ({size} bytes)")
            return foto_path
        else:
            print(f"✗ Error al capturar foto: {result.stderr}")
            return None
            
    except Exception as e:
        print(f"✗ Excepción al capturar foto: {e}")
        return None

def grabar_audio(duracion=5):
    """
    Graba audio durante X segundos usando termux-microphone-record
    Retorna la ruta del archivo o None si falla
    """
    try:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        audio_path = os.path.join(TEMP_DIR, f"audio_{timestamp}.m4a")
        
        print(f"🎤 Grabando audio ({duracion} segundos)...")
        
        # Iniciar grabación
        subprocess.run(
            ["termux-microphone-record", "-f", audio_path, "-l", str(duracion)],
            capture_output=True,
            timeout=duracion + 2
        )
        
        if os.path.exists(audio_path):
            size = os.path.getsize(audio_path)
            print(f"✓ Audio grabado: {audio_path} ({size} bytes)")
            return audio_path
        else:
            print(f"✗ No se pudo crear el archivo de audio")
            return None
            
    except Exception as e:
        print(f"✗ Excepción al grabar audio: {e}")
        return None

def convertir_a_base64(filepath):
    """Convierte un archivo a base64"""
    try:
        with open(filepath, 'rb') as f:
            return base64.b64encode(f.read()).decode('utf-8')
    except Exception as e:
        print(f"✗ Error al convertir a base64: {e}")
        return None

def subir_al_servidor(foto_path, audio_path):
    """
    Sube la foto y audio al servidor principal
    """
    try:
        print(f"\n📤 Preparando envío al servidor...")
        
        # Convertir a base64
        foto_base64 = convertir_a_base64(foto_path) if foto_path else None
        audio_base64 = convertir_a_base64(audio_path) if audio_path else None
        
        if not foto_base64:
            print("✗ No se pudo convertir la foto")
            return False
        
        # Preparar datos
        datos = {
            "imagen": foto_base64,
            "audio": audio_base64,
            "timestamp": datetime.now().isoformat(),
            "dispositivo": "camara_android"
        }
        
        # Enviar al servidor
        print(f"📡 Enviando datos al servidor {SERVIDOR_PRINCIPAL}/api/upload...")
        response = requests.post(
            f"{SERVIDOR_PRINCIPAL}/api/upload",
            json=datos,
            timeout=30
        )
        
        if response.status_code == 200:
            result = response.json()
            print(f"✓ Datos enviados correctamente")
            print(f"   Análisis IA: {result.get('analisis', {})}")
            return True
        else:
            print(f"✗ Error del servidor: {response.status_code}")
            print(f"   Respuesta: {response.text[:200]}")
            return False
            
    except Exception as e:
        print(f"✗ Error al subir datos: {e}")
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
        except Exception as e:
            print(f"⚠️  Error al limpiar temporales: {e}")

# ============================================================================
# ENDPOINTS HTTP
# ============================================================================

@app.route('/health', methods=['GET'])
def health_check():
    """Endpoint de salud para verificar que el servidor está activo"""
    return jsonify({
        "status": "online",
        "dispositivo": "camara_android",
        "timestamp": datetime.now().isoformat()
    })

@app.route('/capturar', methods=['POST'])
def capturar_multimedia():
    """
    Endpoint que recibe comando de captura desde el servidor principal.
    Automáticamente captura foto + audio y los sube al servidor.
    """
    try:
        print("\n" + "=" * 60)
        print("🚨 COMANDO DE CAPTURA RECIBIDO")
        print("=" * 60)
        
        # Obtener parámetros (opcional)
        data = request.get_json() or {}
        duracion_audio = data.get('duracion_audio', 5)
        
        print(f"⚙️  Duración de audio: {duracion_audio} segundos")
        
        # 1. Capturar foto
        foto_path = capturar_foto()
        
        # 2. Grabar audio
        audio_path = grabar_audio(duracion=duracion_audio)
        
        # 3. Verificar que al menos tenemos foto
        if not foto_path:
            return jsonify({
                "success": False,
                "error": "No se pudo capturar la foto"
            }), 500
        
        # 4. Subir al servidor principal
        exito = subir_al_servidor(foto_path, audio_path)
        
        if exito:
            print("\n✅ Proceso completado exitosamente")
            return jsonify({
                "success": True,
                "mensaje": "Foto y audio capturados y enviados correctamente",
                "timestamp": datetime.now().isoformat()
            })
        else:
            print("\n⚠️  Proceso completado con errores")
            return jsonify({
                "success": False,
                "error": "Error al subir datos al servidor"
            }), 500
            
    except Exception as e:
        print(f"\n✗ Error en proceso de captura: {e}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

@app.route('/test', methods=['POST'])
def test_captura():
    """Endpoint de prueba para verificar captura sin enviar al servidor"""
    try:
        print("\n🧪 TEST DE CAPTURA")
        
        # Capturar foto
        foto_path = capturar_foto()
        
        # Grabar audio
        audio_path = grabar_audio(duracion=3)
        
        resultado = {
            "foto_capturada": foto_path is not None,
            "audio_grabado": audio_path is not None,
            "foto_path": foto_path,
            "audio_path": audio_path
        }
        
        print(f"✓ Test completado: {resultado}")
        
        return jsonify(resultado)
        
    except Exception as e:
        print(f"✗ Error en test: {e}")
        return jsonify({"error": str(e)}), 500

# ============================================================================
# MAIN
# ============================================================================

if __name__ == '__main__':
    print("\n🚀 Iniciando servidor de cámara en el teléfono...")
    print(f"📱 Asegúrate de que Termux:API tenga permisos de cámara y micrófono")
    print(f"🌐 El servidor estará disponible en: http://0.0.0.0:{PUERTO_CAMARA}")
    print(f"💡 Para detener el servidor: Ctrl+C")
    print("\n" + "=" * 60 + "\n")
    
    # Iniciar servidor Flask
    app.run(
        host='0.0.0.0',  # Escuchar en todas las interfaces
        port=PUERTO_CAMARA,
        debug=False,
        threaded=True
    )
