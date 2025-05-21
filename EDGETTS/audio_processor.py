# -*- coding: utf-8 -*-
import os
import asyncio
from pydub import AudioSegment
from tts_engine import edge_tts_sintetizar, add_silence, run_async
from openai_client import generar_texto_con_openai
from data_manager import dataframe_a_json

# Carpeta de salida
carpeta_salida = "audios_generados"

async def procesar_entrada_json(indice, df, voz, velocidad, api_key=None):
    """Procesa una entrada de JSON y genera el audio correspondiente"""
    try:
        if indice < 0 or indice >= len(df):
            return None, f"Error: Índice {indice} fuera de rango"
        
        # Convertir DataFrame a lista de diccionarios
        entradas = dataframe_a_json(df)
        entrada = entradas[indice]
        
        # Preparar componentes del audio
        series = entrada["series"]
        part = entrada["part"]
        outro = entrada["outro"]
        
        # Obtener tipo y etiquetas (nuevos campos)
        tipo = entrada.get("tipo", "Historia")
        etiquetas = entrada.get("etiquetas", "")
        
        # Conseguir el texto principal según si es IA o no
        if entrada["IA"]:
            if not entrada["textAI"]:
                return None, "Error: El campo textAI está vacío pero IA está activado"
            
            texto_generado = generar_texto_con_openai(entrada["textAI"], tipo, etiquetas, api_key)
            if texto_generado.startswith("Error:"):
                return None, texto_generado
            texto_principal = texto_generado
        else:
            texto_principal = entrada["text"]
            if not texto_principal:
                return None, "Error: El campo text está vacío pero IA está desactivado"
        
        # Componer el texto completo con pausas representadas por puntos
        intro = f"{series}, parte {part}"
        
        # Generar audio completo
        nombre_archivo_final = os.path.join(carpeta_salida, f"audio_completo_{abs(hash(str(os.urandom(4)))) % 10000000}.mp3")
        
        # Asegurarse de que exista la carpeta de salida
        os.makedirs(carpeta_salida, exist_ok=True)
        
        # Generar componentes por separado y unirlos con silencio
        archivo_intro = await edge_tts_sintetizar(intro, voz, velocidad)
        archivo_texto = await edge_tts_sintetizar(texto_principal, voz, velocidad)
        archivo_outro = await edge_tts_sintetizar(outro, voz, velocidad)
        
        # Unir con silencios usando pydub
        audio_intro = AudioSegment.from_mp3(archivo_intro)
        audio_texto = AudioSegment.from_mp3(archivo_texto)
        audio_outro = AudioSegment.from_mp3(archivo_outro)
        
        silencio = add_silence(500)  # 0.5 segundos de silencio
        
        audio_final = audio_intro + silencio + audio_texto + silencio + audio_outro
        audio_final.export(nombre_archivo_final, format="mp3")
        
        # Limpiar archivos temporales
        try:
            os.remove(archivo_intro)
            os.remove(archivo_texto)
            os.remove(archivo_outro)
        except Exception as e:
            print(f"Advertencia: No se pudieron eliminar archivos temporales: {e}")
        
        return nombre_archivo_final, f"Audio generado exitosamente para '{series}, parte {part}'"
        
    except Exception as e:
        print(f"Error procesando entrada JSON: {e}")
        return None, f"Error: {str(e)}"

def generar_audio_desde_json(indice, df, voz_edge, velocidad, api_key=None):
    """Función para generar audio desde una entrada específica del JSON"""
    try:
        indice = int(indice) - 1  # Convertir a base 0
        if indice < 0:
            return None, "Error: El índice debe ser un número positivo"
            
        resultado = run_async(procesar_entrada_json, indice, df, voz_edge, velocidad, api_key)
        return resultado
    except ValueError:
        return None, "Error: El índice debe ser un número válido"
    except Exception as e:
        return None, f"Error inesperado: {str(e)}"