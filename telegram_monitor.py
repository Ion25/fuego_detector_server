#!/usr/bin/env python3
"""
Monitor de Telegram - Sistema de Detección de Incendios UNSA
Monitorea el bot de Telegram para recibir fotos enviadas por el usuario
"""

import time
import requests
import base64
from datetime import datetime
from telegram_config import TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID

# URL del servidor local
SERVER_URL = "http://localhost:5000"

# Variable para rastrear el último update procesado
last_update_id = 0

def obtener_actualizaciones():
    """Obtiene nuevas actualizaciones del bot de Telegram"""
    global last_update_id
    
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/getUpdates"
    params = {
        "offset": last_update_id + 1,
        "timeout": 30  # Long polling de 30 segundos
    }
    
    try:
        response = requests.get(url, params=params, timeout=35)
        data = response.json()
        
        if data.get("ok"):
            return data.get("result", [])
        else:
            print(f"⚠️  Error en getUpdates: {data.get('description')}")
            return []
    except Exception as e:
        print(f"⚠️  Error al conectar con Telegram: {e}")
        return []

def descargar_foto(file_id):
    """Descarga una foto de Telegram y la convierte a base64"""
    # Obtener ruta del archivo
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/getFile"
    params = {"file_id": file_id}
    
    response = requests.get(url, params=params)
    data = response.json()
    
    if not data.get("ok"):
        print(f"⚠️  Error al obtener archivo: {data.get('description')}")
        return None
    
    file_path = data["result"]["file_path"]
    
    # Descargar archivo
    download_url = f"https://api.telegram.org/file/bot{TELEGRAM_BOT_TOKEN}/{file_path}"
    response = requests.get(download_url)
    
    if response.status_code == 200:
        # Convertir a base64
        imagen_base64 = base64.b64encode(response.content).decode('utf-8')
        return f"data:image/jpeg;base64,{imagen_base64}"
    else:
        print(f"⚠️  Error al descargar foto (código {response.status_code})")
        return None

def enviar_foto_al_servidor(imagen_base64):
    """Envía la foto al servidor para análisis"""
    url = f"{SERVER_URL}/api/upload"
    
    payload = {
        "imagen": imagen_base64,
        "audio": None,
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }
    
    try:
        response = requests.post(url, json=payload, timeout=10)
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Foto enviada al servidor para análisis")
            
            # Mostrar resultado
            if data.get("analisis_ia"):
                ia = data["analisis_ia"]
                if ia["fuego_detectado"]:
                    print(f"🔥 ¡FUEGO DETECTADO! (Confianza: {ia['confianza']:.1f}%)")
                else:
                    print(f"✅ No se detectó fuego (Confianza: {ia['confianza']:.1f}%)")
            
            return True
        else:
            print(f"⚠️  Error del servidor: {response.status_code}")
            return False
    except Exception as e:
        print(f"⚠️  Error al enviar foto al servidor: {e}")
        return False

def enviar_mensaje(texto):
    """Envía un mensaje de confirmación al usuario"""
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": texto,
        "parse_mode": "Markdown"
    }
    
    try:
        requests.post(url, json=payload)
    except:
        pass

def procesar_actualizaciones(updates):
    """Procesa las actualizaciones recibidas de Telegram"""
    global last_update_id
    
    for update in updates:
        update_id = update.get("update_id")
        message = update.get("message", {})
        
        # Actualizar el ID del último update procesado
        if update_id > last_update_id:
            last_update_id = update_id
        
        # Verificar que el mensaje sea del usuario correcto
        chat_id = str(message.get("chat", {}).get("id", ""))
        if chat_id != TELEGRAM_CHAT_ID:
            continue
        
        # Procesar foto
        if "photo" in message:
            photos = message["photo"]
            # Tomar la foto de mayor resolución (última en la lista)
            photo = photos[-1]
            file_id = photo["file_id"]
            
            print(f"📷 Foto recibida de Telegram (file_id: {file_id[:20]}...)")
            
            # Descargar foto
            imagen_base64 = descargar_foto(file_id)
            if imagen_base64:
                print(f"✅ Foto descargada ({len(imagen_base64)} chars)")
                
                # Enviar al servidor
                if enviar_foto_al_servidor(imagen_base64):
                    enviar_mensaje("✅ Foto recibida y analizada correctamente")
                else:
                    enviar_mensaje("⚠️ Error al procesar la foto en el servidor")
            else:
                enviar_mensaje("⚠️ Error al descargar la foto de Telegram")
        
        # Procesar comando de texto
        elif "text" in message:
            texto = message["text"]
            if texto.startswith("/"):
                if texto == "/estado":
                    # Consultar estado del sistema
                    try:
                        response = requests.get(f"{SERVER_URL}/api/estado")
                        if response.status_code == 200:
                            estado = response.json()
                            msg = f"*Estado del Sistema:* {estado['estado']}\n\n"
                            if estado.get("ultima_lectura"):
                                lectura = estado["ultima_lectura"]
                                msg += f"🌡️ Temperatura: {lectura['temperatura']}°C\n"
                                msg += f"💡 Luz: {lectura['luz']} lux\n"
                                msg += f"💧 Humedad: {lectura['humedad']}%\n"
                            enviar_mensaje(msg)
                        else:
                            enviar_mensaje("⚠️ No se pudo obtener el estado del servidor")
                    except:
                        enviar_mensaje("⚠️ Servidor no disponible")

def main():
    """Función principal del monitor"""
    print("=" * 60)
    print("🤖 Monitor de Telegram - Sistema de Detección de Incendios")
    print("   Universidad Nacional de San Agustín")
    print("=" * 60)
    print()
    print(f"📱 Bot: @unsa_fire_bot")
    print(f"👤 Chat ID: {TELEGRAM_CHAT_ID}")
    print()
    print("✅ Monitor iniciado. Esperando fotos de Telegram...")
    print("   (Presiona Ctrl+C para detener)")
    print()
    
    try:
        while True:
            # Obtener actualizaciones
            updates = obtener_actualizaciones()
            
            if updates:
                procesar_actualizaciones(updates)
            
            # Pequeña pausa antes de la siguiente consulta
            time.sleep(0.5)
    
    except KeyboardInterrupt:
        print()
        print("🛑 Monitor detenido por el usuario")
    except Exception as e:
        print(f"❌ Error fatal: {e}")

if __name__ == "__main__":
    main()
