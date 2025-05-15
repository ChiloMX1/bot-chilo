#!/bin/bash

echo "🔄 Subiendo cambios a GitHub..."

# Agrega todos los archivos modificados
git add .

# Crea un commit con fecha y hora
git commit -m "Actualización automática: $(date +'%Y-%m-%d %H:%M:%S')"

# Empuja a la rama main
git push origin main

echo "✅ ¡Listo! Cambios subidos a GitHub."
