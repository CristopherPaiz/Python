import os
from dotenv import load_dotenv
import gradio as gr

# Cargar variables de entorno
load_dotenv()

# Importar los módulos propios
from tts_engine import inicializar_voces
from ui import crear_interfaz

# Crear carpetas necesarias
carpeta_salida = "audios_generados"
os.makedirs(carpeta_salida, exist_ok=True)

# Inicializar voces
voces_edge_tts, voces_espanol = inicializar_voces()

if __name__ == "__main__":
    print("\nIniciando interfaz web. Espera un momento...\n")
    interfaz = crear_interfaz(voces_edge_tts, voces_espanol)
    interfaz.launch(share=False)