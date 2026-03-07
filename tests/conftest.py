"""
Agrega la raíz del proyecto al sys.path para que los imports
de agent.* funcionen sin instalar el paquete.
"""
import sys
import os

# Permite correr pytest desde cualquier directorio
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))