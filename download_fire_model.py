#!/usr/bin/env python3
"""
Script para descargar un modelo pre-entrenado de detección de fuego.
Intenta varias fuentes públicas hasta encontrar una que funcione.
"""

import urllib.request
import os
import sys

# Directorio donde guardar el modelo
MODELS_DIR = os.path.join(os.path.dirname(__file__), "models")
os.makedirs(MODELS_DIR, exist_ok=True)

# Lista de URLs de modelos pre-entrenados (de más confiable a menos)
MODEL_SOURCES = [
    {
        "name": "Fire Detection Model (Kaggle)",
        "url": "https://storage.googleapis.com/kaggle-models/6892/11424/fire_detection_model.tflite?GoogleAccessId=web-data@kaggle-161607.iam.gserviceaccount.com",
        "filename": "fire_model.tflite"
    },
    {
        "name": "MobileNetV2 Fire (GitHub Release)",
        "url": "https://github.com/spacewalk01/yolov5-fire-detection/releases/download/v1.0/fire_detection.tflite",
        "filename": "fire_model.tflite"
    },
]

def download_file(url, dest_path):
    """Descarga un archivo desde una URL"""
    try:
        print(f"📥 Descargando desde: {url}")
        
        # Configurar headers para evitar bloqueos
        req = urllib.request.Request(
            url,
            headers={
                'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36'
            }
        )
        
        with urllib.request.urlopen(req, timeout=30) as response:
            data = response.read()
            
            # Verificar que es un archivo TFLite (empieza con "TFL3" o similar)
            if len(data) > 0 and not data[:15].decode('utf-8', errors='ignore').startswith('<!DOCTYPE'):
                with open(dest_path, 'wb') as f:
                    f.write(data)
                print(f"✅ Descargado: {len(data)} bytes")
                return True
            else:
                print("⚠️  El archivo parece ser HTML, no un modelo TFLite")
                return False
                
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def main():
    print("=" * 60)
    print("🔥 Descargador de Modelo de Detección de Fuego")
    print("=" * 60)
    print()
    
    for source in MODEL_SOURCES:
        print(f"\n🔄 Intentando: {source['name']}")
        dest_path = os.path.join(MODELS_DIR, source['filename'])
        
        if download_file(source['url'], dest_path):
            # Verificar tamaño mínimo
            if os.path.getsize(dest_path) > 10000:  # Al menos 10KB
                print(f"\n✅ ¡Modelo descargado exitosamente!")
                print(f"📁 Ubicación: {dest_path}")
                print(f"📊 Tamaño: {os.path.getsize(dest_path) / 1024:.2f} KB")
                return True
            else:
                print("⚠️  Archivo demasiado pequeño, probablemente no es válido")
                os.remove(dest_path)
    
    print("\n" + "=" * 60)
    print("❌ No se pudo descargar ningún modelo automáticamente")
    print("\n📝 OPCIONES MANUALES:")
    print("=" * 60)
    print()
    print("1️⃣  Descargar modelo desde Google Colab:")
    print("   • Abre: https://colab.research.google.com/")
    print("   • Copia y pega este código:")
    print()
    print("   !wget https://github.com/OlafenwaMoses/FireNET/raw/master/models/fire_model.tflite")
    print("   from google.colab import files")
    print("   files.download('fire_model.tflite')")
    print()
    print("2️⃣  Entrenar tu propio modelo (5-10 min):")
    print("   • Usa Google Teachable Machine: https://teachablemachine.withgoogle.com/")
    print("   • Categorías: 'Fuego' y 'No Fuego'")
    print("   • Exporta como 'TensorFlow Lite'")
    print()
    print("3️⃣  Usar por ahora la heurística de color:")
    print("   • Tu servidor YA FUNCIONA con detección por color")
    print("   • Es menos precisa pero sirve para pruebas")
    print()
    return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
