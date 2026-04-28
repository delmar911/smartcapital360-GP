#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────
# SmartCapital 360° — Script de inicio
# Sistema Inteligente de Control de Accesos
# Proyecto: Gerencia de Proyectos - Politécnico Grancolombiano
# ─────────────────────────────────────────────────────────────

echo "=============================================="
echo "  SmartCapital 360° - Control de Accesos"
echo "  Iniciando servidor de desarrollo..."
echo "=============================================="

# Install dependencies if needed
pip install flask --quiet

# Navigate to backend and start
cd "$(dirname "$0")/backend"
python3 app.py
