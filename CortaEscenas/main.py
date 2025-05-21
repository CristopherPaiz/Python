from datetime import datetime
from datetime import timedelta
import time 
import os
import subprocess
import whisper
import torch
from tqdm import tqdm
from moviepy.config import change_settings
from moviepy.editor import *
import json
from moviepy.editor import VideoFileClip, TextClip, CompositeVideoClip
import pysrt
import os
from translation_utils import TranslationManager

# Configuración de CUDA para MoviePy
import os
os.environ["CUDA_VISIBLE_DEVICES"] = "0"  # Usar la primera GPU

# Verificar si CUDA está disponible
if torch.cuda.is_available():
    print(f"GPU detectada: {torch.cuda.get_device_name(0)}")
    print(f"Memoria GPU total: {torch.cuda.get_device_properties(0).total_memory / 1024**3:.2f} GB")
else:
    print("No se detectó GPU con CUDA")

# Configuración de ImageMagick
IMAGEMAGICK_BINARY = os.getenv('IMAGEMAGICK_BINARY', 'C:\\Program Files\\ImageMagick-7.1.1-Q16-HDRI\\magick.exe')
change_settings({"IMAGEMAGICK_BINARY": IMAGEMAGICK_BINARY})

# =========================================================================
# ------------------------------ CONSTANTES -------------------------------
# =========================================================================

# Dictionary of language codes to full names for Marian MT models
LANGUAGE_PAIRS = {
    'es': {'en': 'Helsinki-NLP/opus-mt-es-en', 'es': None},  # español
    'en': {'es': 'Helsinki-NLP/opus-mt-en-es', 'en': None},  # inglés
    'fr': {'en': 'Helsinki-NLP/opus-mt-fr-en', 'es': 'Helsinki-NLP/opus-mt-fr-es'},  # francés
    'de': {'en': 'Helsinki-NLP/opus-mt-de-en', 'es': 'Helsinki-NLP/opus-mt-de-es'},  # alemán
    'it': {'en': 'Helsinki-NLP/opus-mt-it-en', 'es': 'Helsinki-NLP/opus-mt-it-es'},  # italiano
    'pt': {'en': 'Helsinki-NLP/opus-mt-pt-en', 'es': 'Helsinki-NLP/opus-mt-pt-es'},  # portugués
}

BASE_PATH = r"C:\Users\crist\OneDrive\Documents\Progra\Python\CortaEscenas"

CARPETA_ENTRADA = os.path.join(BASE_PATH, "Entrada")
CARPETA_SALIDA = os.path.join(BASE_PATH, "Salida")
CARPETA_CORTOS = os.path.join(BASE_PATH, "Cortos")
CARPETA_ARCHIVOS = os.path.join(BASE_PATH, "Archivos necesarios")

MIN_ESCENAS = 5
MAX_ESCENAS = 100
DURACION_CORTO_SEGUNDOS = 40  # ejemplo: 5 minutos
MIN_DURACION_ESCENA = 10 * 1000  # 10 segundos en milisegundos
MAX_DURACION_ESCENA = 30 * 1000  # 30 segundos en milisegundos
MARGEN_DURACION = 10  # 30 segundos de margen aceptable (+ o -) para duración de corto


# Nombre de modelo Whisper
WHISPER_MODEL = "medium" # tiny, base, small, medium, large large-v2. large-v3, turbo

# =========================================================================
# --------------------------- FUNCIONES AUX -------------------------------
# =========================================================================

def imprimir_paso(mensaje: str):
    """
    Imprime el mensaje prefijado con [INFO] para tener seguimiento de pasos.
    """
    print(f"[INFO] {mensaje}")

# =========================================================================
# --------------------------- SELECCIÓN DE IDIOMA -------------------------
# =========================================================================

def seleccionar_opcion_idioma():
    print("Seleccione la opción de subtitulado:")
    print("  1. Inglés a Español")
    print("  2. Español a Inglés")
    print("  3. Automático (detecta el idioma y traduce al idioma que especifiques)")
    opcion = input("Ingrese una opción (1-3): ").strip()
    
    if opcion == "1":
        return {
            "modo": "traduccion",
            "modelo": WHISPER_MODEL,
            "task": "transcribe",
            "source_lang": "en",
            "target_lang": "es",
            "descripcion": "Traduce este contenido audiovisual de Inglés a Español"
        }
    elif opcion == "2":
        return {
            "modo": "traduccion",
            "modelo": WHISPER_MODEL,
            "task": "transcribe",
            "source_lang": "es",
            "target_lang": "en",
            "descripcion": "Traduce este contenido audiovisual de Español a Inglés"
        }
    else:
        print("\nIdiomas disponibles (códigos):")
        print("  es: Español")
        print("  en: Inglés")
        print("  fr: Francés")
        print("  de: Alemán")
        print("  it: Italiano")
        print("  pt: Portugués")
        target_lang = input("\nIngrese el código del idioma destino: ").strip().lower()
        
        return {
            "modo": "auto",
            "modelo": WHISPER_MODEL,
            "task": "transcribe",
            "source_lang": "auto",
            "target_lang": target_lang,
            "descripcion": f"Idioma Automático a idioma: {target_lang}"
        }
      
# =========================================================================
# --------------------- TRANSCRIPCIÓN Y TRADUCCIÓN ------------------------
# =========================================================================

def transcribir_whisper(video_path, config):
    """
    Ejecuta Whisper usando el modelo para transcribir y traducir
    """
    imprimir_paso(f"Transcribiendo con Whisper: {video_path}")
    
    try:
        output_dir = os.path.dirname(video_path)
        base_name = os.path.splitext(os.path.basename(video_path))[0]
        
        # Cargar el modelo de Whisper
        try:
            model = whisper.load_model(config["modelo"])
        except Exception as e:
            imprimir_paso(f"Error al cargar el modelo: {str(e)}")
            raise
        
        imprimir_paso(f"Transcribiendo desde {config['source_lang']} a {config['target_lang']}")
        
        # Primero, obtener la transcripción en el idioma original
        result = model.transcribe(
            video_path,
            language=config["source_lang"],
            task="transcribe",
            verbose=True,
            fp16=False,
            no_speech_threshold= 0.6,  # Más estricto en detectar silencio
            compression_ratio_threshold= 2.4,  # Ajuste para evitar repeticiones
            condition_on_previous_text= True,  # Usar contexto previo
            word_timestamps= True,     # Habilitar timestamps por palabra
            best_of= 5,               # Aumentar precisión con múltiples candidatos
            beam_size= 5,       # Búsqueda en haz para mejor segmentación
        )
        
        # Preparar segmentos
        segments = [{
            "start": seg["start"],
            "end": seg["end"],
            "text": seg["text"].strip()
        } for seg in result["segments"]]
        
        # Si necesitamos traducir
        if config["source_lang"] != config["target_lang"]:
            imprimir_paso(f"Traduciendo de {config['source_lang']} a {config['target_lang']}")
            translator = TranslationManager()
            segments = translator.translate_segments(
                segments, 
                config["source_lang"], 
                config["target_lang"]
            )
        
        # Generar archivo SRT
        output_path = os.path.join(output_dir, f"{base_name}.srt")
        with open(output_path, "w", encoding="utf-8") as f:
            for i, seg in enumerate(segments, start=1):
                start_time = format_timestamp(seg["start"])
                end_time = format_timestamp(seg["end"])
                text = seg["text"].strip()
                if text:  # Solo escribir si hay texto
                    f.write(f"{i}\n")
                    f.write(f"{start_time} --> {end_time}\n")
                    f.write(f"{text}\n\n")
        
        if os.path.exists(output_path) and os.path.getsize(output_path) > 0:
            imprimir_paso("Proceso completado exitosamente")
            return output_path
        else:
            raise Exception("No se generó el archivo de subtítulos")

    except Exception as e:
        imprimir_paso(f"Error: {str(e)}")
        raise

def parse_srt_file(srt_path):
    """
    Parsea un archivo SRT y retorna una lista de segments
    """
    segments = []
    current_segment = {}
    
    with open(srt_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()
        
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        
        # Saltar líneas vacías
        if not line:
            i += 1
            continue
        
        # Número de subtítulo
        if line.isdigit():
            i += 1
            continue
        
        # Tiempos
        if ' --> ' in line:
            times = line.split(' --> ')
            if len(times) == 2:
                start = sum(float(x) * 60 ** i for i, x in enumerate(reversed(times[0].replace(',', '.').split(':'))))
                end = sum(float(x) * 60 ** i for i, x in enumerate(reversed(times[1].replace(',', '.').split(':'))))
                current_segment = {"start": start, "end": end}
                
                # Leer el texto
                text_lines = []
                i += 1
                while i < len(lines) and lines[i].strip():
                    text_lines.append(lines[i].strip())
                    i += 1
                
                current_segment["text"] = ' '.join(text_lines)
                segments.append(current_segment)
                continue
        
        i += 1
    
    return segments

def format_timestamp(seconds):
    """
    Convierte segundos a formato de tiempo SRT (HH:MM:SS,mmm)
    """
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    millis = int((seconds - int(seconds)) * 1000)
    return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"

def generar_subtitulos(video_path, config):
    """
    Genera subtítulos usando Whisper CLI con sistema de reintentos y 
    parsea el contenido del archivo SRT generado
    """
    max_intentos = 3
    ultimo_error = None
    
    for intento in range(max_intentos):
        try:
            imprimir_paso(f"Generando subtítulos (Intento {intento + 1}/{max_intentos})")
            srt_path = transcribir_whisper(video_path, config)
            
            # Verificar que el archivo SRT existe y tiene contenido
            if os.path.exists(srt_path) and os.path.getsize(srt_path) > 0:
                imprimir_paso(f"Subtítulos generados exitosamente: {srt_path}")
                
                # Parse del archivo SRT a formato de segmentos
                segments = parse_srt_file(srt_path)
                
                if segments:
                    return segments
                else:
                    raise Exception("No se pudieron extraer segmentos del archivo SRT")
                
            else:
                raise Exception("El archivo de subtítulos está vacío o no se generó")
            
        except Exception as e:
            ultimo_error = str(e)
            imprimir_paso(f"Error en intento {intento + 1}: {ultimo_error}")
            
            if intento < max_intentos - 1:
                tiempo_espera = (intento + 1) * 5
                imprimir_paso(f"Esperando {tiempo_espera} segundos antes de reintentar...")
                time.sleep(tiempo_espera)
            else:
                imprimir_paso("Se agotaron los intentos de transcripción")
                raise Exception(f"Fallaron todos los intentos. Último error: {ultimo_error}")
                           
# =========================================================================1
# -------------------------- CREACIÓN DE SRT ------------------------------
# =========================================================================

def generar_srt_file(segments, srt_path):
    """
    Crea un archivo SRT con la lista de segments [{start, end, text}, ...].
    """
    imprimir_paso(f"Generando archivo SRT: {srt_path}")
    
    def srt_time(segundos):
        hrs = int(segundos // 3600)
        mins = int((segundos % 3600) // 60)
        secs = int(segundos % 60)
        ms = int((segundos - int(segundos)) * 1000)
        return f"{hrs:02}:{mins:02}:{secs:02},{ms:03}"
    
    with open(srt_path, "w", encoding="utf-8") as f:
        for i, seg in enumerate(segments, start=1):
            inicio = srt_time(seg["start"])
            fin = srt_time(seg["end"])
            texto = seg["text"].strip()
            
            f.write(f"{i}\n")
            f.write(f"{inicio} --> {fin}\n")
            f.write(f"{texto}\n\n")

# =========================================================================
# --------------------------- HARD-SUB (FFmpeg) ---------------------------
# =========================================================================

def archivo_ya_procesado(video_file, carpeta_salida):
    """
    Verifica si un video ya fue procesado previamente y todos sus archivos existen
    """
    base_name = os.path.splitext(video_file)[0]
    video_path = os.path.join(carpeta_salida, video_file)
    srt_path = os.path.join(carpeta_salida, base_name + ".srt")
    
    # Verificar si ambos archivos existen y el video tiene tamaño
    if os.path.exists(video_path) and os.path.exists(srt_path):
        if os.path.getsize(video_path) > 0:
            # Verificar que el video tenga stream de video
            try:
                probe_cmd = [
                    "ffprobe",
                    "-v", "error",
                    "-select_streams", "v:0",
                    "-show_entries", "stream=codec_type",
                    "-of", "json",
                    video_path
                ]
                result = subprocess.run(probe_cmd, capture_output=True, text=True)
                video_info = json.loads(result.stdout)
                if video_info.get("streams"):
                    return True
            except:
                pass
    return False

def calcular_tamanio_subtitulo(width, height):
    """Calcula el tamaño de subtítulo óptimo basado en la resolución del video"""
    # Base: 1080p -> tamaño 36
    # Proporción basada en el ancho del video
    tamanio_base = 46
    factor_escala = width / 1920  # 1920 es el ancho de referencia (1080p)
    
    # Ajustar el tamaño mínimo y máximo
    tamanio = max(20, min(72, int(tamanio_base * factor_escala)))
    return tamanio + 10

def aplicar_hardsub_ffmpeg(input_video, input_srt, output_video):
    try:
        imprimir_paso(f"Procesando video: {input_video}")
        
        # Asegurar que el output_video termine en .mp4
        if not output_video.lower().endswith('.mp4'):
            output_video = os.path.splitext(output_video)[0] + '.mp4'
            imprimir_paso(f"Ajustando nombre de salida a: {output_video}")

        # Verificar el codec de audio del input
        probe_cmd = [
            "ffprobe",
            "-v", "error",
            "-select_streams", "a:0",
            "-show_entries", "stream=codec_name",
            "-of", "json",
            input_video
        ]
        
        audio_codec = None
        try:
            result = subprocess.run(probe_cmd, capture_output=True, text=True)
            audio_info = json.loads(result.stdout)
            if audio_info.get("streams"):
                audio_codec = audio_info["streams"][0].get("codec_name")
                imprimir_paso(f"Codec de audio detectado: {audio_codec}")
        except Exception as e:
            imprimir_paso(f"No se pudo detectar el codec de audio: {str(e)}")

        # Si el audio no es AAC, primero convertir el video a MP4 con audio AAC
        temp_video = None
        video_to_process = input_video
        
        if audio_codec and audio_codec.lower() != 'aac':
            imprimir_paso("Convirtiendo audio a AAC...")
            temp_video = os.path.join(
                os.path.dirname(output_video),
                f"temp_{os.path.basename(output_video)}"
            )
            
            convert_cmd = [
                "ffmpeg", "-y",
                "-i", input_video,
                "-c:v", "copy",
                "-c:a", "aac",
                "-b:a", "192k",
                temp_video
            ]
            
            try:
                subprocess.run(convert_cmd, check=True, capture_output=True)
                video_to_process = temp_video
                imprimir_paso("Conversión de audio completada")
            except subprocess.CalledProcessError as e:
                imprimir_paso(f"Error en la conversión de audio: {e.stderr.decode()}")
                if temp_video and os.path.exists(temp_video):
                    os.remove(temp_video)
                return False

        try:
            # Cargar el video ya convertido
            video = VideoFileClip(video_to_process)
            
            # Calcular tamaño de subtítulo
            tamanio_subtitulo = calcular_tamanio_subtitulo(video.w, video.h)
            imprimir_paso(f"Tamaño de subtítulo: {tamanio_subtitulo}px para resolución {video.w}x{video.h}")
            
            # Cargar subtítulos
            subs = pysrt.open(input_srt)
            text_clips = []
            
            for sub in subs:
                start_time = sub.start.ordinal / 1000
                end_time = sub.end.ordinal / 1000
                duration = end_time - start_time

                sys.stdout.write('\033[K' + f'\rCargando: [{str(timedelta(seconds=int(start_time)))}] {sub.text[:90]}{"..." if len(sub.text) > 90 else ""}')

                posicion_vertical = int(video.h * 0.87 if len(sub.text) <= 90 else video.h * 0.82)

                txt_clip = (TextClip(sub.text, 
                                fontsize=tamanio_subtitulo, 
                                font='Calibri-Bold',
                                color='white',
                                stroke_color='black',
                                stroke_width=2,
                                size=(video.w * 0.87, None),
                                method='caption')
                        .set_position(('center', posicion_vertical))
                        .set_duration(duration)
                        .set_start(start_time))
                
                text_clips.append(txt_clip)
            
            print()  # Nueva línea después del progreso
            
            # Combinar video y subtítulos
            final_video = CompositeVideoClip([video] + text_clips)
            
            # Intentar codificación con configuración optimizada
            try:
                imprimir_paso(f"Codificando video con {os.cpu_count()} hilos...")
                final_video.write_videofile(
                    output_video,
                    codec="libx264",
                    preset="ultrafast",
                    audio_codec="aac",
                    audio=True,
                    fps=30,
                    threads=os.cpu_count(),
                    ffmpeg_params=[
                        '-crf', '23',
                        '-movflags', '+faststart',
                        '-bf', '2',
                        '-b:a', '192k'
                    ]
                )
            except Exception as codec_error:
                imprimir_paso(f"Error con codificación rápida, intentando configuración alternativa: {str(codec_error)}")
                final_video.write_videofile(
                    output_video,
                    codec='libx264',
                    preset='fast',
                    audio_codec="aac",
                    audio=True,
                    fps=video.fps,
                    threads=os.cpu_count(),
                    ffmpeg_params=[
                        '-crf', '23',
                        '-movflags', '+faststart',
                        '-bf', '2',
                        '-b:a', '192k'
                    ]
                )
            
            # Limpiar
            video.close()
            final_video.close()
            for clip in text_clips:
                clip.close()
                
            # Eliminar archivo temporal si existe
            if temp_video and os.path.exists(temp_video):
                os.remove(temp_video)
                
            imprimir_paso(f"Video procesado exitosamente: {output_video}")
            return True
            
        except Exception as e:
            imprimir_paso(f"Error en el procesamiento del video: {str(e)}")
            if temp_video and os.path.exists(temp_video):
                os.remove(temp_video)
            return False
            
    except Exception as e:
        imprimir_paso(f"Error general: {str(e)}")
        return False
    
# =========================================================================
# --------------------------- CREACIÓN DE CORTOS --------------------------
# =========================================================================

def detectar_o_cargar_escenas(video_path):
    """
    Detecta escenas del video o las carga de un archivo cache si existe
    """
    # Crear nombre del archivo cache
    base_name = os.path.splitext(os.path.basename(video_path))[0]
    cache_file = os.path.join(os.path.dirname(video_path), f"{base_name}_escenas.json")
    
    # Verificar si existe el cache
    if os.path.exists(cache_file):
        imprimir_paso(f"Cargando escenas desde cache: {cache_file}")
        try:
            with open(cache_file, 'r') as f:
                escenas = json.load(f)
            imprimir_paso(f"Escenas cargadas del cache: {len(escenas)}")
            return [(float(start), float(end)) for start, end in escenas]
        except Exception as e:
            imprimir_paso(f"Error al cargar cache: {str(e)}")
    
    # Si no existe cache, detectar escenas
    imprimir_paso(f"Detectando escenas en: {video_path}")
    try:
        from scenedetect import SceneManager, VideoManager
        from scenedetect.detectors import ContentDetector
    except ImportError:
        imprimir_paso("ADVERTENCIA: PySceneDetect no instalado. No se cortarán escenas.")
        return []
    
    video_manager = VideoManager([video_path])
    scene_manager = SceneManager()
    scene_manager.add_detector(ContentDetector())
    
    video_manager.set_downscale_factor()
    video_manager.start()
    scene_manager.detect_scenes(frame_source=video_manager)
    
    scene_list = scene_manager.get_scene_list(video_manager.get_base_timecode())
    escenas = [(scene[0].get_seconds(), scene[1].get_seconds()) for scene in scene_list]
    
    # Guardar en cache
    try:
        with open(cache_file, 'w') as f:
            json.dump(escenas, f)
        imprimir_paso(f"Escenas guardadas en cache: {cache_file}")
    except Exception as e:
        imprimir_paso(f"Error al guardar cache: {str(e)}")
    
    return escenas

def crear_cortos(video_path, output_folder):
    """
    Crea cortos mediante la combinación inteligente de escenas distribuidas a lo largo del video.
    """
    imprimir_paso(f"Creando cortos para: {video_path}")
    
    # Verificar que el video tenga streams de video y audio
    probe_command = [
        "ffprobe",
        "-v", "error",
        "-select_streams", "v:0",  # stream de video
        "-show_entries", "stream=duration",
        "-of", "json",
        video_path
    ]
    
    try:
        result = subprocess.run(probe_command, capture_output=True, text=True)
        video_info = json.loads(result.stdout)
        if not video_info.get("streams"):
            imprimir_paso("Error: El archivo no contiene un stream de video válido")
            return
    except Exception as e:
        imprimir_paso(f"Error al verificar el video: {str(e)}")
        return

    # 1. Detectar escenas base
    escenas = detectar_o_cargar_escenas(video_path)
    if not escenas or len(escenas) < 2:
        imprimir_paso("No hay suficientes escenas para crear un corto.")
        return
    
    # Obtener duración total del video
    duracion_video = escenas[-1][1]
    imprimir_paso(f"Duración total del video: {duracion_video:.2f} segundos")

    # 2. Calcular duración objetivo del corto basado en la duración del video
    # Para videos de 5 min a 1 hora
    if duracion_video <= 300:  # 5 minutos
        duracion_objetivo = min(60, duracion_video * 0.8)  # 50% del video o 1 minuto máximo
    elif duracion_video <= 3600:  # 1 hora
        duracion_objetivo = min(300, duracion_video * 0.3)  # 15% del video o 5 minutos máximo
    else:
        duracion_objetivo = 300  # 5 minutos máximo para videos más largos

    # 3. Establecer parámetros de duración de escenas
    MIN_DURACION_ESCENA = 10  # segundos
    MAX_DURACION_ESCENA = 30  # segundos
    MARGEN_DURACION = 5  # segundos de margen aceptable

    # 4. Agrupar escenas contiguas que sean muy cortas
    escenas_agrupadas = []
    escena_actual = list(escenas[0])
    
    for i in range(1, len(escenas)):
        duracion_actual = escena_actual[1] - escena_actual[0]
        
        if duracion_actual < MIN_DURACION_ESCENA and i < len(escenas):
            # Extender la escena actual
            escena_actual[1] = escenas[i][1]
        else:
            if MIN_DURACION_ESCENA <= duracion_actual <= MAX_DURACION_ESCENA:
                escenas_agrupadas.append(tuple(escena_actual))
            elif duracion_actual > MAX_DURACION_ESCENA:
                # Dividir en segmentos de MAX_DURACION_ESCENA
                tiempo_inicio = escena_actual[0]
                while tiempo_inicio < escena_actual[1]:
                    tiempo_fin = min(tiempo_inicio + MAX_DURACION_ESCENA, escena_actual[1])
                    escenas_agrupadas.append((tiempo_inicio, tiempo_fin))
                    tiempo_inicio = tiempo_fin
            escena_actual = list(escenas[i])
    
    # Agregar la última escena si cumple los criterios
    duracion_ultima = escena_actual[1] - escena_actual[0]
    if MIN_DURACION_ESCENA <= duracion_ultima <= MAX_DURACION_ESCENA:
        escenas_agrupadas.append(tuple(escena_actual))

    # 5. Distribuir escenas a lo largo del video
    escenas_agrupadas.sort(key=lambda x: x[0])  # Ordenar por tiempo de inicio
    num_escenas_objetivo = int(duracion_objetivo / 20)  # Aproximadamente una escena cada 20 segundos
    
    # Calcular el paso para distribuir las escenas uniformemente
    if len(escenas_agrupadas) > num_escenas_objetivo:
        paso = len(escenas_agrupadas) / num_escenas_objetivo
        indices_seleccionados = [int(i * paso) for i in range(num_escenas_objetivo)]
        segmentos_finales = [escenas_agrupadas[i] for i in indices_seleccionados if i < len(escenas_agrupadas)]
    else:
        segmentos_finales = escenas_agrupadas

    # 6. Ajustar la duración total
    duracion_total = sum(end - start for start, end in segmentos_finales)
    
    while duracion_total > duracion_objetivo + MARGEN_DURACION and len(segmentos_finales) > 2:
        # Remover el segmento más largo
        segmento_mas_largo = max(segmentos_finales, key=lambda x: x[1] - x[0])
        segmentos_finales.remove(segmento_mas_largo)
        duracion_total = sum(end - start for start, end in segmentos_finales)

    if not segmentos_finales:
        imprimir_paso("No se pudieron seleccionar suficientes segmentos")
        return

    # 7. Ordenar los segmentos por tiempo
    segmentos_finales.sort(key=lambda x: x[0])

    # 8. Crear el video final con FFmpeg
    try:
        filter_complex = []
        for i, (start, end) in enumerate(segmentos_finales):
            # Agregar filtros para video y audio
            filter_complex.extend([
                f"[0:v]trim=start={start:.3f}:end={end:.3f},setpts=PTS-STARTPTS[v{i}]",
                f"[0:a]atrim=start={start:.3f}:end={end:.3f},asetpts=PTS-STARTPTS[a{i}]"
            ])

        # Agregar la concatenación
        v_parts = ''.join(f'[v{i}]' for i in range(len(segmentos_finales)))
        a_parts = ''.join(f'[a{i}]' for i in range(len(segmentos_finales)))
        filter_complex.append(
            f"{v_parts}concat=n={len(segmentos_finales)}:v=1:a=0[vout];"
            f"{a_parts}concat=n={len(segmentos_finales)}:v=0:a=1[aout]"
        )

        # Unir todos los filtros
        filter_string = ';'.join(filter_complex)

        # Preparar el nombre del archivo de salida
        output_path = os.path.join(
            output_folder, 
            f"{os.path.splitext(os.path.basename(video_path))[0]}_corto.mp4"
        )

        # Comando FFmpeg
        command = [
            "ffmpeg", "-y",
            "-i", video_path,
            "-filter_complex", filter_string,
            "-map", "[vout]",
            "-map", "[aout]",
            "-c:v", "libx264",
            "-preset", "fast",
            "-crf", "23",
            "-c:a", "aac",
            "-b:a", "192k",
            output_path
        ]

        # Mostrar información sobre los segmentos
        imprimir_paso(f"Creando corto con {len(segmentos_finales)} segmentos distribuidos...")
        imprimir_paso("Distribución de segmentos:")
        for i, (start, end) in enumerate(segmentos_finales, 1):
            imprimir_paso(f"Segmento {i}: {start:.1f}s - {end:.1f}s (duración: {end-start:.1f}s)")

        # Ejecutar FFmpeg
        result = subprocess.run(command, capture_output=True, text=True)

        if result.returncode != 0:
            imprimir_paso(f"Error de FFmpeg: {result.stderr}")
            return

        # Verificar el resultado
        if os.path.exists(output_path) and os.path.getsize(output_path) > 1024:
            imprimir_paso(f"Corto creado exitosamente: {output_path}")
            imprimir_paso(f"Duración total aproximada: {duracion_total:.2f} segundos")
            imprimir_paso(f"Número de segmentos: {len(segmentos_finales)}")
            imprimir_paso(f"Cobertura del video original: {(segmentos_finales[0][0]/duracion_video)*100:.1f}% - {(segmentos_finales[-1][1]/duracion_video)*100:.1f}%")
        else:
            imprimir_paso("Error: El archivo de salida no se creó correctamente")

    except Exception as e:
        imprimir_paso(f"Error durante la creación del corto: {str(e)}")
        
# =========================================================================
# ------------------------------- MAIN ------------------------------------
# =========================================================================

def main():
    imprimir_paso("##############################################################################################################")
    print("Hora inicio: ", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    tiempo_inicio = datetime.now()
    
    # Asegurar carpetas
    for carpeta in [CARPETA_ENTRADA, CARPETA_SALIDA, CARPETA_CORTOS, CARPETA_ARCHIVOS]:
        if not os.path.isdir(carpeta):
            os.makedirs(carpeta, exist_ok=True)
    
    # Seleccionar modo de subtitulado
    config_idioma = seleccionar_opcion_idioma()
    imprimir_paso(f"Opción seleccionada => {config_idioma['descripcion']}")
    
    # Lista de videos en carpeta de entrada
    videos = [v for v in os.listdir(CARPETA_ENTRADA) if v.lower().endswith(".ts") or v.lower().endswith(".mp4")]
    imprimir_paso(f"Total de videos a procesar: {len(videos)}")
    
    # 1) Generar SRT y Quemar Subtítulos
    print("Hora inicio de procesamiento: ", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    for video_file in tqdm(videos, desc="Procesar Videos"):
        video_path = os.path.join(CARPETA_ENTRADA, video_file)
        base_name = os.path.splitext(video_file)[0]
        
        srt_path = os.path.join(CARPETA_SALIDA, base_name + ".srt")
        hardsub_video_path = os.path.join(CARPETA_SALIDA, video_file)
        
        # Verificar si el video ya fue procesado completamente
        if archivo_ya_procesado(video_file, CARPETA_SALIDA):
            imprimir_paso(f"Video ya procesado anteriormente: {video_file}")
            continue
        
        # Si existe el SRT pero no el video, hay que procesar el video
        if os.path.exists(srt_path) and not os.path.exists(hardsub_video_path):
            imprimir_paso(f"SRT existe pero falta el video con subtítulos: {video_file}")
            # Hacer hardsub con el SRT existente
            exito = aplicar_hardsub_ffmpeg(video_path, srt_path, hardsub_video_path)
            if not exito:
                imprimir_paso(f"Falla en hardsub para: {video_file}")
                continue
        # Si no existe ni el SRT ni el video, procesar todo
        elif not os.path.exists(srt_path):
            imprimir_paso(f"No existe SRT para {video_file}, generándolo...")
            segs_finales = generar_subtitulos(video_path, config_idioma)
            generar_srt_file(segs_finales, srt_path)
            
            # Hacer hardsub con el nuevo SRT
            exito = aplicar_hardsub_ffmpeg(video_path, srt_path, hardsub_video_path)
            if not exito:
                imprimir_paso(f"Falla en hardsub para: {video_file}")
                continue
    
    # 2) Crear cortos de los videos hardsubeados
    print("Hora inicio de creación de cortos: ", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    imprimir_paso("Iniciando creación de cortos para videos ya subtitulados")
    videos_subtitulados = [v for v in os.listdir(CARPETA_SALIDA) if v.lower().endswith(".mp4")]
    
    for video_file in tqdm(videos_subtitulados, desc="Cortos"):
        video_path = os.path.join(CARPETA_SALIDA, video_file)
        crear_cortos(video_path, CARPETA_CORTOS)
    
    tiempo_total = datetime.now() - tiempo_inicio
    print("Hora fin de procesamiento: ", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    print("Tiempo total de procesamiento: ", tiempo_total)
    imprimir_paso("Proceso finalizado.")
    imprimir_paso("##############################################################################################################")

if __name__ == "__main__":
    main()