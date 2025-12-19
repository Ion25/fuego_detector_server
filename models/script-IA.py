"""
Sistema de Detección de Incendios con YOLOv8
Analiza imágenes en busca de fuego y humo
"""

import os
import sys
from pathlib import Path
import json

# Instalación de dependencias necesarias:
# pip install ultralytics opencv-python pillow torch torchvision

def install_dependencies():
    """Instala las dependencias necesarias"""
    print("Instalando dependencias...")
    os.system("pip install ultralytics opencv-python pillow torch torchvision")

def download_fire_model():
    """
    Descarga un modelo YOLOv8 pre-entrenado para detección de incendios
    Usaremos un modelo de Roboflow Universe o entrenaremos uno básico
    """
    from ultralytics import YOLO
    
    # Opción 1: Usar YOLOv8 base y fine-tunearlo (recomendado)
    # Para esta demo, usamos YOLOv8n (nano) por velocidad
    print("Descargando modelo YOLOv8...")
    model = YOLO('yolov8n.pt')  # Modelo base
    
    # Nota: Para producción, deberías usar un modelo específico de incendios
    # Ejemplo: model = YOLO('fire_detection_model.pt')
    
    return model

def analyze_image_colors(image_path):
    """
    Análisis complementario basado en colores
    Detecta patrones de color rojo/naranja/amarillo
    """
    import cv2
    import numpy as np
    
    img = cv2.imread(str(image_path))
    if img is None:
        return {"fire_detected": False, "confidence": 0}
    
    # Convertir a HSV para mejor detección de colores
    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
    
    # Rangos de color para fuego
    # Rojo (fuego intenso)
    lower_red1 = np.array([0, 100, 100])
    upper_red1 = np.array([10, 255, 255])
    lower_red2 = np.array([160, 100, 100])
    upper_red2 = np.array([180, 255, 255])
    
    # Naranja-Amarillo (llamas)
    lower_orange = np.array([10, 100, 100])
    upper_orange = np.array([30, 255, 255])
    
    mask_red1 = cv2.inRange(hsv, lower_red1, upper_red1)
    mask_red2 = cv2.inRange(hsv, lower_red2, upper_red2)
    mask_orange = cv2.inRange(hsv, lower_orange, upper_orange)
    
    mask_fire = mask_red1 | mask_red2 | mask_orange
    
    # Calcular porcentaje de píxeles de fuego
    total_pixels = img.shape[0] * img.shape[1]
    fire_pixels = cv2.countNonZero(mask_fire)
    fire_percentage = (fire_pixels / total_pixels) * 100
    
    # Detección más estricta
    fire_detected = fire_percentage > 3.0  # Al menos 3% de la imagen
    confidence = min(fire_percentage * 10, 100)  # Normalizar a 0-100
    
    return {
        "fire_detected": fire_detected,
        "confidence": round(confidence, 2),
        "fire_percentage": round(fire_percentage, 2)
    }

def analyze_with_yolo(model, image_path):
    """
    Analiza una imagen usando YOLOv8
    Para demo usamos el modelo base, pero en producción
    usarías un modelo específico entrenado para fuego/humo
    """
    try:
        results = model.predict(
            source=str(image_path),
            conf=0.25,  # Confianza mínima
            verbose=False
        )
        
        # En un modelo real de incendios, buscarías clases como:
        # 'fire', 'smoke', 'flames'
        # Por ahora, con el modelo base buscamos objetos relacionados
        
        fire_related_classes = []
        max_confidence = 0
        
        for result in results:
            if result.boxes is not None:
                for box in result.boxes:
                    conf = float(box.conf[0])
                    cls = int(box.cls[0])
                    class_name = model.names[cls]
                    
                    # Registrar objetos detectados
                    if conf > max_confidence:
                        max_confidence = conf
                    
                    fire_related_classes.append({
                        "class": class_name,
                        "confidence": round(conf * 100, 2)
                    })
        
        return {
            "objects_detected": fire_related_classes,
            "max_confidence": round(max_confidence * 100, 2)
        }
    
    except Exception as e:
        print(f"Error en análisis YOLO: {e}")
        return {"objects_detected": [], "max_confidence": 0}

def detect_fire_in_images(images_folder, model=None):
    """
    Analiza todas las imágenes en la carpeta especificada
    Retorna un diccionario con los resultados
    """
    images_path = Path(images_folder)
    
    if not images_path.exists():
        return {
            "success": False,
            "error": f"Carpeta {images_folder} no existe"
        }
    
    # Obtener todas las imágenes
    image_files = []
    for ext in ['*.jpg', '*.jpeg', '*.png', '*.JPG', '*.JPEG', '*.PNG']:
        image_files.extend(images_path.glob(ext))
    
    if len(image_files) == 0:
        return {
            "success": False,
            "error": "No se encontraron imágenes en la carpeta"
        }
    
    print(f"\n🔍 Analizando {len(image_files)} imágenes...")
    
    results = {
        "success": True,
        "total_images": len(image_files),
        "fire_detected": False,
        "images_with_fire": [],
        "details": []
    }
    
    for img_path in image_files:
        print(f"\n📸 Analizando: {img_path.name}")
        
        # Análisis por colores (más confiable para esta demo)
        color_analysis = analyze_image_colors(img_path)
        
        # Análisis con YOLO (opcional, comentado por ahora)
        yolo_analysis = {"objects_detected": [], "max_confidence": 0}
        if model is not None:
            yolo_analysis = analyze_with_yolo(model, img_path)
        
        # Decisión final combinando ambos métodos
        fire_detected = color_analysis["fire_detected"]
        confidence = color_analysis["confidence"]
        
        image_result = {
            "filename": img_path.name,
            "fire_detected": fire_detected,
            "confidence": confidence,
            "color_analysis": color_analysis,
            "yolo_analysis": yolo_analysis
        }
        
        results["details"].append(image_result)
        
        if fire_detected:
            results["images_with_fire"].append(img_path.name)
            print(f"  🔥 FUEGO DETECTADO - Confianza: {confidence}%")
        else:
            print(f"  ✓ Sin incendio detectado")
    
    # Si al menos una imagen tiene fuego, activar alerta
    results["fire_detected"] = len(results["images_with_fire"]) > 0
    
    return results

def main():
    """Función principal"""
    
    # Configuración
    IMAGES_FOLDER = "/uploads/images"  # Cambia esta ruta según tu servidor
    
    # Si se pasa una ruta como argumento
    if len(sys.argv) > 1:
        IMAGES_FOLDER = sys.argv[1]
    
    print("=" * 60)
    print("🔥 SISTEMA DE DETECCIÓN DE INCENDIOS")
    print("=" * 60)
    
    # Nota: Para esta demo usamos solo análisis de colores
    # Para producción, descarga un modelo específico de incendios
    model = None
    
    # Descomentar esto si quieres usar YOLO:
    # try:
    #     model = download_fire_model()
    #     print("✓ Modelo YOLO cargado")
    # except Exception as e:
    #     print(f"⚠ No se pudo cargar modelo YOLO: {e}")
    #     print("  Usando solo análisis de colores...")
    
    # Analizar imágenes
    results = detect_fire_in_images(IMAGES_FOLDER, model)
    
    # Mostrar resultados
    print("\n" + "=" * 60)
    print("📊 RESULTADOS DEL ANÁLISIS")
    print("=" * 60)
    print(f"Total de imágenes analizadas: {results.get('total_images', 0)}")
    print(f"Imágenes con fuego detectado: {len(results.get('images_with_fire', []))}")
    print(f"\n🚨 ALERTA DE INCENDIO: {'SÍ' if results['fire_detected'] else 'NO'}")
    
    if results["fire_detected"]:
        print(f"\n🔥 Archivos con fuego:")
        for filename in results["images_with_fire"]:
            print(f"   - {filename}")
    
    # Guardar resultados en JSON
    output_file = Path(IMAGES_FOLDER) / "fire_detection_results.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    
    print(f"\n💾 Resultados guardados en: {output_file}")
    
    # Retornar código de salida
    # 0 = no hay fuego, 1 = hay fuego
    sys.exit(1 if results["fire_detected"] else 0)

if __name__ == "__main__":
    main()
