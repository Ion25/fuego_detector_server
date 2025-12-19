#!/bin/bash

# Script de configuración para Ubuntu
# Fire Detection Server - UNSA

echo "=================================="
echo "🔥 Fire Detection Server - Setup"
echo "=================================="

# Verificar Python 3
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 no está instalado"
    echo "   Instala con: sudo apt install python3 python3-pip python3-venv"
    exit 1
fi

echo "✅ Python 3 encontrado: $(python3 --version)"

# Crear entorno virtual
echo ""
echo "📦 Creando entorno virtual..."
python3 -m venv venv

# Activar entorno virtual
echo "✅ Entorno virtual creado"
echo ""
echo "🔧 Activando entorno virtual..."
source venv/bin/activate

# Actualizar pip
echo ""
echo "⬆️  Actualizando pip..."
pip install --upgrade pip

# Instalar dependencias
echo ""
echo "📥 Instalando dependencias..."
pip install -r requirements.txt

echo ""
echo "=================================="
echo "✅ Instalación completada"
echo "=================================="
echo ""
echo "Para iniciar el servidor:"
echo "  1. Activa el entorno virtual: source venv/bin/activate"
echo "  2. Ejecuta el servidor: python server.py"
echo ""
echo "O simplemente ejecuta: ./start.sh"
echo ""
