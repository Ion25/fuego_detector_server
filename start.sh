#!/bin/bash

# Script para iniciar el servidor
# Fire Detection Server - UNSA

echo "🔥 Iniciando Fire Detection Server..."
echo ""

# Verificar si existe el entorno virtual
if [ ! -d "venv" ]; then
    echo "❌ Entorno virtual no encontrado"
    echo "   Ejecuta primero: ./setup.sh"
    exit 1
fi

# Activar entorno virtual
source venv/bin/activate

# Ejecutar servidor
python server.py
