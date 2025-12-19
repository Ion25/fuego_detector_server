# Guía de Contribución

¡Gracias por tu interés en contribuir al Sistema IoT de Detección de Incendios! 🔥

## 🚀 Cómo Contribuir

### Reportar Bugs

Si encuentras un bug, por favor abre un issue incluyendo:

- **Descripción clara** del problema
- **Pasos para reproducir** el error
- **Comportamiento esperado** vs. comportamiento actual
- **Entorno**: Sistema operativo, versión de Python, hardware usado
- **Logs relevantes** (si están disponibles)

### Proponer Mejoras

Para proponer nuevas características:

1. Abre un issue con etiqueta `enhancement`
2. Describe claramente la funcionalidad propuesta
3. Explica el caso de uso y beneficios
4. Si es posible, proporciona ejemplos o mockups

### Enviar Pull Requests

1. **Fork** el repositorio
2. **Crea una rama** desde `main`:
   ```bash
   git checkout -b feature/nombre-descriptivo
   ```
3. **Realiza tus cambios** siguiendo las guías de estilo
4. **Prueba** tus cambios exhaustivamente
5. **Commit** con mensajes descriptivos:
   ```bash
   git commit -m "Add: nueva funcionalidad X"
   git commit -m "Fix: corrección del bug Y"
   git commit -m "Docs: actualización de README"
   ```
6. **Push** a tu fork:
   ```bash
   git push origin feature/nombre-descriptivo
   ```
7. **Abre un Pull Request** hacia la rama `main`

## 📝 Guías de Estilo

### Python

- Seguir [PEP 8](https://pep8.org/)
- Usar nombres descriptivos para variables y funciones
- Documentar funciones con docstrings
- Mantener líneas de máximo 100 caracteres
- Usar type hints cuando sea posible

```python
def calcular_umbral(temperatura: float, luz: float) -> str:
    """
    Evalúa el estado del sistema según umbrales de temperatura y luz.
    
    Args:
        temperatura: Temperatura en grados Celsius
        luz: Intensidad luminosa en lux
        
    Returns:
        Estado del sistema: "Normal", "Alerta" o "Peligro"
    """
    # Implementación...
```

### JavaScript

- Usar `const` y `let`, evitar `var`
- Preferir arrow functions
- Comentarios claros y concisos

### Arduino C++

- Comentarios explicativos en español
- Usar constantes para pines y valores configurables
- Validar lecturas de sensores

## 🧪 Testing

Antes de enviar un PR:

1. Prueba manualmente todas las funcionalidades afectadas
2. Si es posible, añade tests automatizados
3. Verifica que no introduces nuevos warnings o errores

## 📚 Documentación

- Actualiza el README.md si añades nuevas features
- Documenta nuevos endpoints en la API
- Añade comentarios en código complejo

## 🔄 Proceso de Revisión

- Los mantenedores revisarán tu PR en 2-5 días hábiles
- Se pueden solicitar cambios o mejoras
- Una vez aprobado, tu contribución será mergeada

## 💡 Áreas Prioritarias

Especialmente buscamos contribuciones en:

- **Modelos de IA**: Integración de modelos de Deep Learning entrenados
- **Optimización**: Mejoras de rendimiento y uso de recursos
- **Testing**: Creación de suite de tests automatizados
- **Documentación**: Traducciones, tutoriales, videos
- **Hardware**: Soporte para más tipos de sensores
- **Interfaz**: Mejoras del dashboard y UX

## 🤔 ¿Tienes Dudas?

No dudes en:

- Abrir un issue con etiqueta `question`
- Contactar a los mantenedores
- Revisar issues existentes

## 🎓 Primera Contribución

Si es tu primera vez contribuyendo a un proyecto open source:

- Busca issues con etiqueta `good first issue`
- Lee la documentación completa
- No tengas miedo de preguntar

¡Toda contribución, por pequeña que sea, es valiosa! 🙌
