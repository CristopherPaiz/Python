# -*- coding: utf-8 -*-
import os
import time
import asyncio
import edge_tts
from pydub import AudioSegment
import re

# Carpeta de salida para los audios generados
carpeta_salida = "audios_generados"
if not os.path.exists(carpeta_salida):
    os.makedirs(carpeta_salida)

# Voz por defecto (nombre corto y nombre completo)
voz_defecto_corta = "es-BO-MarceloNeural"
voz_defecto_completa = "es-BO-MarceloNeural - Microsoft Server Speech Text to Speech Voice (es-BO, MarceloNeural) (Male)"

# Diccionario de idiomas para mostrar en formato amigable
idiomas = {
    'es-AR': 'Español Argentina',
    'es-BO': 'Español Bolivia',
    'es-CL': 'Español Chile',
    'es-CO': 'Español Colombia',
    'es-CR': 'Español Costa Rica',
    'es-CU': 'Español Cuba',
    'es-DO': 'Español República Dominicana',
    'es-EC': 'Español Ecuador',
    'es-ES': 'Español España',
    'es-GQ': 'Español Guinea Ecuatorial',
    'es-GT': 'Español Guatemala',
    'es-HN': 'Español Honduras',
    'es-MX': 'Español México',
    'es-NI': 'Español Nicaragua',
    'es-PA': 'Español Panamá',
    'es-PE': 'Español Perú',
    'es-PR': 'Español Puerto Rico',
    'es-PY': 'Español Paraguay',
    'es-SV': 'Español El Salvador',
    'es-US': 'Español Estados Unidos',
    'es-UY': 'Español Uruguay',
    'es-VE': 'Español Venezuela'
}

# Contador global para numerar los audios
contador_audios = 1

def run_async(func, *args, **kwargs):
    """Ejecuta una función asíncrona de manera segura"""
    loop = asyncio.new_event_loop()
    try:
        result = loop.run_until_complete(func(*args, **kwargs))
        return result
    finally:
        loop.close()

async def obtener_voces_edge_tts():
    try:
        voces = await edge_tts.list_voices()
        print(f"Voces Edge TTS disponibles: {len(voces)}")
        return voces
    except Exception as e:
        print(f"Error al obtener voces de Edge TTS: {e}")
        return []

def formatear_nombre_voz(nombre_corto, nombre_completo):
    """Formatea el nombre de voz en un formato amigable"""
    try:
        # Extraer el nombre simple
        nombre_simple = nombre_corto.split("-")[-1].replace("Neural", " Neural")
        
        # Extraer el código de idioma (es-XX)
        codigo_idioma = "-".join(nombre_corto.split("-")[0:2])
        
        # Determinar el idioma basado en el código
        idioma = idiomas.get(codigo_idioma, codigo_idioma)
        
        # Determinar el género
        genero = "Masculino" if "(Male)" in nombre_completo else "Femenino"
        
        return f"{nombre_simple} - {idioma}, ({genero})"
    except:
        return nombre_corto

def inicializar_voces():
    """Inicializa y devuelve las listas de voces disponibles"""
    try:
        voces_edge_tts = run_async(obtener_voces_edge_tts)
        
        if voces_edge_tts:
            nombres_voces_edge = []
            voces_espanol_formateadas = []
            
            for voz in voces_edge_tts:
                nombre_corto = voz.get('ShortName', '')
                nombre = voz.get('Name', nombre_corto)
                genero = f" ({voz.get('Gender', 'Unknown')})" if 'Gender' in voz else ''
                
                nombre_completo = f"{nombre_corto} - {nombre}{genero}"
                nombres_voces_edge.append(nombre_completo)
                
                # Separar y formatear las voces en español
                if nombre_corto.startswith('es-'):
                    nombre_formateado = formatear_nombre_voz(nombre_corto, nombre_completo)
                    voces_espanol_formateadas.append((nombre_completo, nombre_formateado, nombre_corto))
            
            print(f"Total voces Edge TTS disponibles: {len(nombres_voces_edge)}")
            
            # Ordenar las voces en español alfabéticamente
            voces_espanol_formateadas.sort(key=lambda x: x[1])
            
            # Crear la lista numerada de voces en español
            voces_espanol_numeradas = []
            for i, (nombre_completo, nombre_formateado, nombre_corto) in enumerate(voces_espanol_formateadas, 1):
                texto_numerado = f"{i}. {nombre_formateado}"
                voces_espanol_numeradas.append((nombre_completo, texto_numerado, nombre_corto))
            
            print(f"Voces en español disponibles: {len(voces_espanol_numeradas)}")
            print("\nVOCES EN ESPAÑOL DISPONIBLES:")
            for _, texto_numerado, _ in voces_espanol_numeradas:
                print(texto_numerado)
            print("\nVoz predeterminada:")
            for _, texto_numerado, nombre_corto in voces_espanol_numeradas:
                if nombre_corto == voz_defecto_corta:
                    print(f"→ {texto_numerado}")
                    break
        else:
            nombres_voces_edge = ["No se pudieron cargar las voces"]
            voces_espanol_numeradas = []
            print("No se pudo obtener la lista de voces")
    except Exception as e:
        print(f"Error procesando voces: {e}")
        nombres_voces_edge = ["Error al procesar voces"]
        voces_espanol_numeradas = []

    return nombres_voces_edge, voces_espanol_numeradas

def limpiar_texto_para_nombre_archivo(texto):
    """Limpia el texto para usarlo como parte del nombre de archivo"""
    # Limitar a los primeros 30 caracteres para el nombre del archivo
    texto_corto = texto[:30].strip()
    # Eliminar caracteres no permitidos en nombres de archivo
    return re.sub(r'[\\/*?:"<>|]', "", texto_corto).replace(" ", "_")

def obtener_voz_por_numero(numero, voces_espanol_numeradas):
    """Obtiene la voz completa por su número en la lista"""
    if 1 <= numero <= len(voces_espanol_numeradas):
        return voces_espanol_numeradas[numero-1][0]  # Devuelve el nombre completo
    return voz_defecto_completa

async def edge_tts_sintetizar(texto, voz=voz_defecto_corta, velocidad=1.0):
    """Sintetiza texto a voz usando Edge TTS"""
    global contador_audios
    
    try:
        # Si recibimos el nombre completo, extraemos la parte corta
        if " - " in voz:
            nombre_voz = voz.split(" - ")[0]
        else:
            nombre_voz = voz
            
        texto_limpio = limpiar_texto_para_nombre_archivo(texto)
        
        # Crear nombre de archivo con formato: NUM_voz_texto.mp3
        nombre_archivo = os.path.join(
            carpeta_salida, 
            f"{contador_audios:03d}_{nombre_voz}_{texto_limpio}.mp3"
        )
        
        if abs(velocidad - 1.0) < 0.01:  # Si la velocidad es aproximadamente 1.0
            communicate = edge_tts.Communicate(texto, nombre_voz)
        else:
            rate_string = f"+{int((velocidad-1)*100)}%" if velocidad > 1 else f"{int((velocidad-1)*100)}%"
            communicate = edge_tts.Communicate(texto, nombre_voz, rate=rate_string)
        
        await communicate.save(nombre_archivo)
        contador_audios += 1
        
        return nombre_archivo
    except Exception as e:
        print(f"Error en Edge TTS: {e}")
        raise e

def sintetizar_voz(texto, voz=voz_defecto_corta, velocidad=1.0):
    """Función para generar audio desde texto"""
    if not texto:
        return None, "Error: Por favor ingresa un texto para convertir a voz."
    
    try:
        nombre_archivo = run_async(edge_tts_sintetizar, texto, voz, velocidad)
        return nombre_archivo, f"¡Audio #{contador_audios-1} generado con éxito!"
    except Exception as e:
        print(f"Error en síntesis: {e}")
        return None, f"Error al generar audio: {str(e)}"

def add_silence(duration_ms=500):
    """Crear un segmento de silencio"""
    return AudioSegment.silent(duration=duration_ms)

def mostrar_info_audio(nombre_archivo):
    """Muestra información formateada sobre el audio generado"""
    if nombre_archivo:
        num_audio = os.path.basename(nombre_archivo).split('_')[0]
        voz = os.path.basename(nombre_archivo).split('_')[1]
        texto_archivo = '_'.join(os.path.basename(nombre_archivo).split('_')[2:]).replace('.mp3', '')
        
        print("=" * 60)
        print(f"AUDIO #{num_audio}")
        print("-" * 60)
        print(f"Voz: {voz}")
        print(f"Texto: {texto_archivo.replace('_', ' ')}")
        print(f"Archivo: {nombre_archivo}")
        print("=" * 60)