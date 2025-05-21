# -*- coding: utf-8 -*-
import streamlit as st
import edge_tts
import asyncio
import re
import os
import tempfile
from pydub import AudioSegment # Importante para dividir
import aiofiles
from openai import OpenAI
from dotenv import load_dotenv
import random
import subprocess
import time
from pathlib import Path
import datetime
import shutil
import yt_dlp
import google.generativeai as genai
import math # Para calcular chunks

#######################################################################################
# CORRER EN TERMINAL: streamlit run narrator_tts.py
# REQUISITO: FFmpeg debe estar instalado y en el PATH del sistema.
# REQUISITO: yt-dlp debe estar instalado (pip install yt-dlp)
# REQUISITO: google-generativeai debe estar instalado (pip install google-generativeai)
#######################################################################################

# --- Carga de Variables de Entorno ---
load_dotenv()

# --- Configuración de Clientes API ---
# OpenAI
openai_api_key = os.getenv("OPENAI_API_KEY")
if not openai_api_key:
    st.error("CRÍTICO: Variable de entorno OPENAI_API_KEY no encontrada.")
    st.stop()
try:
    client = OpenAI(api_key=openai_api_key)
except Exception as e:
    st.error(f"Error al inicializar cliente OpenAI: {e}")
    st.stop()

# Gemini (Google Generative AI)
gemini_api_key = os.getenv("GEMINI_API_KEY")
if not gemini_api_key:
    st.error("CRÍTICO: Variable de entorno GEMINI_API_KEY no encontrada.")
    st.stop()
try:
    genai.configure(api_key=gemini_api_key)
except Exception as e:
    st.error(f"Error al configurar la API de Gemini: {e}")
    st.stop()

# Modelo Gemini
GEMINI_MODEL_NAME = "gemini-2.5-pro-preview-05-06" # Modelo recomendado y potente

# --- Constantes de la Aplicación ---
CROSSFADE_DURATION_MS = 450
PAUSE_BETWEEN_SECTIONS_MS = 800
DEFAULT_VOICE_SPEED = 1.0
DEFAULT_SPEED_SLIDER_VALUE = 1.0
MIN_SPEED_VALUE = 1.0
MAX_SPEED_VALUE = 2.0
SPEED_STEP = 0.1
SAMPLE_TEXT = "Este es un ejemplo de esta voz."
TEMP_AUDIO_FILE_PATTERN = "part_{:03d}.mp3"
GENERATED_AUDIO_FILENAME = "generated_audio_{}.mp3"
GENERATED_VIDEO_FILENAME = "generated_video_{}.mp4"
DEFAULT_DOWNLOAD_FILENAME_AUDIO = "narracion.mp3"
DEFAULT_DOWNLOAD_FILENAME_VIDEO = "video_narrado.mp4"
OUTPUT_SUBDIR = "generated_files"
# !!! IMPORTANTE: AJUSTA ESTA RUTA A TU CARPETA REAL DE VIDEOS BASE !!!
VIDEO_SOURCE_FOLDER = Path("C:/Users/crist/OneDrive/Documents/Progra/Python/NewEdgeTTS/VIDEOS")
VIDEO_FILENAME_PATTERN = r"(\d{2})_(\d{2})_(\d{2})_.*\.mp4"
SPANISH_LOCALE_PREFIX = "es-"
SCRIPT_TEXT_AREA_HEIGHT = 250
SCRIPT_PLACEHOLDER = "[Narrador1] Hola\n\n[Narrador2] Qué haces\n\n[Narrador3] Te estabamos esperando"
NARRATOR_INPUT_PLACEHOLDER = "Opcional: Narrador4, Narrador5..."
TITLE_PLACEHOLDER = "Introduce el título aquí"
OUTRO_PLACEHOLDER = "Introduce el texto de cierre aquí"
VIDEO_PREVIEW_WIDTH = 240
TITLE_NARRATOR_NAME = "Título"
OUTRO_NARRATOR_NAME = "Outro"

# Duración máxima de cada fragmento de audio para Whisper (en milisegundos)
# 15 minutos (900,000 ms) es un límite seguro para 192kbps MP3 vs 25MB API limit.
WHISPER_CHUNK_DURATION_MS = 15 * 60 * 1000

FILTERED_VOICES = {
    "female": {
        "es-CL-CatalinaNeural (Female - es-CL)": {"id": "es-CL-CatalinaNeural", "display": "CatalinaNeural (Chile)", "speed": 1.1},
        "es-BO-SofiaNeural (Female - es-BO)": {"id": "es-BO-SofiaNeural", "display": "SofiaNeural (Bolivia)", "speed": 1.1},
        "es-AR-ElenaNeural (Female - es-AR)": {"id": "es-AR-ElenaNeural", "display": "ElenaNeural (Argentina)", "speed": 1.1},
        "es-CO-SalomeNeural (Female - es-CO)": {"id": "es-CO-SalomeNeural", "display": "SalomeNeural (Colombia)", "speed": 1.2},
        "es-ES-XimenaNeural (Female - es-ES)": {"id": "es-ES-XimenaNeural", "display": "XimenaNeural (España)", "speed": 1.1},
        "es-CU-BelkysNeural (Female - es-CU)": {"id": "es-CU-BelkysNeural", "display": "BelkysNeural (Cuba)", "speed": 1.2},
        "es-PY-TaniaNeural (Female - es-PY)": {"id": "es-PY-TaniaNeural", "display": "TaniaNeural (Paraguay)", "speed": 1.1},
        "es-UY-ValentinaNeural (Female - es-UY)": {"id": "es-UY-ValentinaNeural", "display": "ValentinaNeural (Uruguay)", "speed": 1.1}
    },
    "male": {
        "es-CL-LorenzoNeural (Male - es-CL)": {"id": "es-CL-LorenzoNeural", "display": "LorenzoNeural (Chile)", "speed": 1.1},
        "es-BO-MarceloNeural (Male - es-BO)": {"id": "es-BO-MarceloNeural", "display": "MarceloNeural (Bolivia)", "speed": 1.1},
        "es-AR-TomasNeural (Male - es-AR)": {"id": "es-AR-TomasNeural", "display": "TomasNeural (Argentina)", "speed": 1.1},
        "es-CO-GonzaloNeural (Male - es-CO)": {"id": "es-CO-GonzaloNeural", "display": "GonzaloNeural (Colombia)", "speed": 1.1},
        "es-ES-AlvaroNeural (Male - es-ES)": {"id": "es-ES-AlvaroNeural", "display": "AlvaroNeural (España)", "speed": 1.1},
        "es-CU-ManuelNeural (Male - es-CU)": {"id": "es-CU-ManuelNeural", "display": "ManuelNeural (Cuba)", "speed": 1.2},
        "es-PY-MarioNeural (Male - es-PY)": {"id": "es-PY-MarioNeural", "display": "MarioNeural (Paraguay)", "speed": 1.1},
        "es-UY-MateoNeural (Male - es-UY)": {"id": "es-UY-MateoNeural", "display": "MateoNeural (Uruguay)", "speed": 1.1}
    }
}

# --- Inicialización de session_state ---
# Gestión del método de entrada y sus datos asociados
if 'input_method' not in st.session_state: st.session_state.input_method = "youtube"
if 'youtube_url' not in st.session_state: st.session_state.youtube_url = ""
if 'transcription_result' not in st.session_state: st.session_state.transcription_result = None
if 'gemini_result' not in st.session_state: st.session_state.gemini_result = None
if 'edited_gemini_content' not in st.session_state: st.session_state.edited_gemini_content = ""
if 'generate_prompt' not in st.session_state: st.session_state.generate_prompt = ""
if 'generate_option' not in st.session_state: st.session_state.generate_option = "Historia"
if 'generated_content' not in st.session_state: st.session_state.generated_content = None
if 'edited_content' not in st.session_state: st.session_state.edited_content = ""

# Contenido y configuración de la narración final
if 'title_text' not in st.session_state: st.session_state.title_text = ""
if 'script' not in st.session_state: st.session_state.script = "" # El guión final aceptado
if 'outro_enabled' not in st.session_state: st.session_state.outro_enabled = False
if 'outro_text' not in st.session_state: st.session_state.outro_text = ""
if 'script_narrators' not in st.session_state: st.session_state.script_narrators = []
if 'narrator_voices' not in st.session_state: st.session_state.narrator_voices = {}
if 'narrator_speeds' not in st.session_state: st.session_state.narrator_speeds = {}
if 'additional_narrators' not in st.session_state: st.session_state.additional_narrators = []
if 'gender_selection' not in st.session_state: st.session_state.gender_selection = {}

# Resultados de la generación final
if 'generated_audio_path' not in st.session_state: st.session_state.generated_audio_path = None
if 'generated_video_path' not in st.session_state: st.session_state.generated_video_path = None
if 'last_run_timestamp' not in st.session_state: st.session_state.last_run_timestamp = None

# --- Crear Directorio de Salida ---
try:
    Path(OUTPUT_SUBDIR).mkdir(parents=True, exist_ok=True)
except OSError as e:
    st.error(f"Error al crear el directorio de salida '{OUTPUT_SUBDIR}': {e}")
    st.stop()

# --- Funciones Auxiliares Generales ---

def generate_with_openai(prompt, option):
    """Genera contenido usando OpenAI GPT."""
    if option == "Historia":
        system_prompt = os.getenv("PROMPT_SYSTEM_HISTORIA", "Eres un asistente útil que crea historias.") # Fallback
        user_prompt = os.getenv("PROMPT_CHATGPT_HISTORIA", "Crea una historia sobre: ") + prompt
    elif option == "Curiosidades":
        system_prompt = os.getenv("PROMPT_SYSTEM_CURIOSIDADES", "Eres un asistente útil que lista curiosidades.")
        user_prompt = os.getenv("PROMPT_CHATGPT_CURIOSIDADES", "Lista curiosidades sobre: ") + prompt
    else:
        st.error(f"Opción de OpenAI no soportada: {option}")
        return ""

    if not system_prompt or not user_prompt:
         st.error("Error: Faltan prompts de OpenAI en variables de entorno (.env).")
         return ""

    def remove_parentheses(text):
        return re.sub(r'\([^)]*\)', '', text).strip()

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            seed=abs(hash(prompt + option)) % 10000000,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.7
        )
        content = response.choices[0].message.content.strip()
        return remove_parentheses(content)
    except Exception as e:
        st.error(f"Error al generar contenido con OpenAI: {str(e)}")
        return ""

def process_with_gemini(text, status_placeholder):
    """Procesa el texto transcrito con Gemini para formatearlo como guión."""
    prompt_template = os.getenv("PROMPT_GEMINI_HISTORIA", "Formatea la siguiente transcripción como un guión narrado:\n\n") # Fallback
    if not prompt_template:
        st.error("Error: Variable de entorno PROMPT_GEMINI_HISTORIA no configurada.")
        return None

    full_prompt = prompt_template + text

    try:
        status_placeholder.text(f"✨ Procesando transcripción con Gemini ({GEMINI_MODEL_NAME})...")
        model = genai.GenerativeModel(GEMINI_MODEL_NAME)
        # Llamada SIN safety_settings
        response = model.generate_content(full_prompt)

        if response.text:
            status_placeholder.text("✅ Procesamiento con Gemini completado.")
            return response.text.strip()
        else:
            reason = "Razón desconocida"
            try: # Safe access to response attributes
                 if response.prompt_feedback and response.prompt_feedback.block_reason:
                      reason = f"Bloqueado: {response.prompt_feedback.block_reason}"
                 elif response.candidates and response.candidates[0].finish_reason:
                      reason = f"Finalizado: {response.candidates[0].finish_reason}"
                 else:
                      reason = "Respuesta vacía."
            except Exception:
                 pass
            st.error(f"Gemini ({GEMINI_MODEL_NAME}) no devolvió texto útil. {reason}")
            print(f"--- Respuesta Gemini (sin texto útil) ---\n{response}\n------------------------------------")
            return None

    except Exception as e:
        st.error(f"Error durante la llamada a Gemini API ({GEMINI_MODEL_NAME}): {e}")
        return None

# --- Función Descarga YouTube ---
def download_youtube_video_and_extract_audio(url, status_placeholder):
    """
    Descarga video de YouTube (360p MP4) y extrae audio a MP3 usando FFmpeg.
    """
    temp_dir = tempfile.mkdtemp()
    video_filename = "youtube_video.mp4"
    audio_filename = "extracted_audio.mp3"
    video_path = Path(temp_dir) / video_filename
    audio_path = Path(temp_dir) / audio_filename

    ydl_opts = {
        'format': 'bestvideo[height<=360][ext=mp4]+bestaudio[ext=m4a]/best[height<=360][ext=mp4]/best[height<=360]',
        'outtmpl': str(video_path),
        'quiet': True,
        'no_warnings': True,
        'noprogress': True,
        'noplaylist': True,
    }

    try:
        status_placeholder.text("📥 Descargando video YouTube (360p MP4)...")
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])

        if not video_path.exists() or video_path.stat().st_size == 0:
            raise yt_dlp.utils.DownloadError("Archivo video vacío/no encontrado tras descarga.")

        status_placeholder.text("🎬 Video descargado. Extrayendo audio (FFmpeg)...")
        ffmpeg_cmd = [
            'ffmpeg', '-i', str(video_path), '-vn', '-acodec', 'libmp3lame',
            '-ab', '192k', '-ar', '44100', '-y', str(audio_path)
        ]

        try:
            result = subprocess.run(ffmpeg_cmd, capture_output=True, text=True, check=True, encoding='utf-8', errors='ignore')
            if result.stderr and any(err in result.stderr.lower() for err in ["error", "fail", "invalid"]):
                 st.warning(f"FFmpeg reportó problemas extracción:\n{result.stderr[:500]}...")

            if not audio_path.exists() or audio_path.stat().st_size == 0:
                raise Exception("Fallo extracción audio FFmpeg (MP3 vacío/no creado).")

            status_placeholder.text("✅ Audio MP3 extraído.")
            return str(audio_path), temp_dir

        except FileNotFoundError:
            st.error("Error Crítico: FFmpeg no encontrado. Instálalo en el PATH.")
            raise
        except subprocess.CalledProcessError as e:
            st.error(f"FFmpeg falló extracción (código {e.returncode}):\n{e.stderr}")
            raise
        except Exception as e_ffmpeg:
             st.error(f"Error extracción FFmpeg: {e_ffmpeg}")
             raise

    except yt_dlp.utils.DownloadError as e_dl:
        st.error(f"Error yt-dlp descarga video: {e_dl}")
        if os.path.isdir(temp_dir): shutil.rmtree(temp_dir)
        return None, None
    except Exception as e_main:
        st.error(f"Error proceso obtención audio: {e_main}")
        if os.path.isdir(temp_dir): shutil.rmtree(temp_dir)
        return None, None
    finally:
        if video_path.exists():
            try:
                os.remove(video_path)
            except OSError as e_clean:
                print(f"Adv: No se pudo limpiar video temp {video_path}: {e_clean}")

# --- Función Transcripción Whisper con Chunking ---
def transcribe_audio_whisper(audio_path_str, status_placeholder):
    """
    Transcribe audio MP3 usando Whisper, dividiendo en fragmentos si es necesario.
    """
    audio_path = Path(audio_path_str)
    if not audio_path.exists():
        st.error(f"Audio MP3 no existe: {audio_path}")
        return None

    full_transcript = ""
    chunk_files_to_clean = []

    try:
        status_placeholder.text("🎙️ Cargando audio para transcripción...")
        audio = AudioSegment.from_file(audio_path)
        duration_ms = len(audio)
        status_placeholder.text(f"Duración total: {duration_ms / 1000:.1f}s. Preparando fragmentos...")

        num_chunks = math.ceil(duration_ms / WHISPER_CHUNK_DURATION_MS)
        if num_chunks == 0:
             st.warning("Audio vacío o demasiado corto.")
             return ""

        status_placeholder.text(f"Dividiendo en {num_chunks} fragmento(s) para Whisper...")

        for i in range(num_chunks):
            start_ms = i * WHISPER_CHUNK_DURATION_MS
            end_ms = min((i + 1) * WHISPER_CHUNK_DURATION_MS, duration_ms)
            chunk = audio[start_ms:end_ms]

            chunk_fd, chunk_path_str = tempfile.mkstemp(suffix=".mp3")
            os.close(chunk_fd)
            chunk_path = Path(chunk_path_str)
            chunk_files_to_clean.append(chunk_path)

            status_placeholder.text(f"Exportando fragmento {i + 1}/{num_chunks} ({start_ms//1000}s - {end_ms//1000}s)...")
            try:
                chunk.export(chunk_path, format="mp3")
                if chunk_path.stat().st_size == 0:
                    st.warning(f"Fragmento {i+1} vacío. Saltando.")
                    continue
            except Exception as e_export:
                st.warning(f"Error exportando fragmento {i+1}: {e_export}. Saltando.")
                continue

            status_placeholder.text(f"Transcribiendo fragmento {i + 1}/{num_chunks} con Whisper...")
            try:
                with open(chunk_path, "rb") as chunk_file:
                    response = client.audio.transcriptions.create(
                        model="whisper-1",
                        file=chunk_file,
                        response_format="text"
                    )
                transcript_part = response if isinstance(response, str) else str(response)
                full_transcript += transcript_part + " "
                status_placeholder.text(f"Fragmento {i + 1}/{num_chunks} transcrito.")

            except Exception as e_whisper:
                st.warning(f"Error transcribiendo fragmento {i + 1}: {e_whisper}. Saltando.")

        status_placeholder.text("✅ Transcripción completada (todos los fragmentos).")
        return full_transcript.strip()

    except Exception as e:
        st.error(f"Error general durante transcripción con fragmentos: {e}")
        return None
    finally:
        for chunk_file_path in chunk_files_to_clean:
            if chunk_file_path.exists():
                try:
                    os.remove(chunk_file_path)
                except OSError as e_clean_chunk:
                    print(f"Adv: No se pudo limpiar chunk {chunk_file_path}: {e_clean_chunk}")

# --- Funciones TTS y Narradores ---
async def get_voices():
    """Obtiene lista de voces de Edge TTS."""
    try:
        return await edge_tts.list_voices()
    except Exception as e:
        st.error(f"Error obtener voces EdgeTTS: {e}")
        return []

@st.cache_data
def load_filtered_voices():
    """Devuelve diccionario predefinido de voces."""
    return FILTERED_VOICES

async def generate_sample(voice_id, speed=DEFAULT_SPEED_SLIDER_VALUE):
    """Genera audio de muestra."""
    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".mp3")
    temp_file.close()
    audio_data = None
    try:
        rate_str = f"{int((speed - 1) * 100):+}%"
        communicate = edge_tts.Communicate(SAMPLE_TEXT, voice_id, rate=rate_str)
        await communicate.save(temp_file.name)
        async with aiofiles.open(temp_file.name, mode='rb') as f:
            audio_data = await f.read()
    except Exception as e:
         st.error(f"Error generando muestra para {voice_id}: {e}")
    finally:
        if os.path.exists(temp_file.name):
            os.unlink(temp_file.name)
    return audio_data

def get_narrator_voice_settings(narrator_name, default_gender="female"):
    """Obtiene voz_id y velocidad para narrador, usando defaults."""
    voice_id = None
    speed = None

    # Intentar desde session_state
    if narrator_name in st.session_state.narrator_voices:
        voice_info = st.session_state.narrator_voices[narrator_name]
        if isinstance(voice_info, dict) and "id" in voice_info:
            voice_id = voice_info["id"]
            speed = st.session_state.narrator_speeds.get(narrator_name, voice_info.get("speed"))

    # Si falla, usar defaults
    if voice_id is None or speed is None:
        gender = st.session_state.gender_selection.get(narrator_name, default_gender)
        try:
            if gender not in FILTERED_VOICES or not FILTERED_VOICES[gender]:
                raise ValueError(f"No hay voces config. para género '{gender}'.")

            default_voice_info = list(FILTERED_VOICES[gender].values())[0]
            voice_id = default_voice_info["id"]
            speed = default_voice_info.get("speed", DEFAULT_SPEED_SLIDER_VALUE)

            # Guardar defaults en estado
            st.session_state.narrator_voices[narrator_name] = default_voice_info
            st.session_state.narrator_speeds[narrator_name] = speed

        except Exception as e:
             st.error(f"Fallo obtener voz default para '{narrator_name}' ({gender}): {e}.")
             # Fallback final (primera voz femenina)
             try:
                 fallback_voice_info = list(FILTERED_VOICES["female"].values())[0]
                 voice_id = fallback_voice_info["id"]
                 speed = DEFAULT_VOICE_SPEED
                 st.warning(f"Usando fallback: {voice_id}")
             except Exception:
                  st.error("¡FALLBACK FALLÓ! No hay voces femeninas config.")
                  voice_id = None # Indicar fallo total
                  speed = DEFAULT_VOICE_SPEED

    return voice_id, speed

async def _generate_single_part(text, voice_id, speed, output_path):
    """Genera MP3 para un segmento de texto."""
    if not text or not voice_id:
        st.warning(f"Saltando parte: Texto/Voz ID faltante (Voz: {voice_id})")
        return False
    try:
        rate_str = f"{int((speed - 1) * 100):+}%"
        communicate = edge_tts.Communicate(text, voice_id, rate=rate_str)
        await communicate.save(output_path)
        if os.path.exists(output_path) and os.path.getsize(output_path) > 100:
            return True
        else:
             st.warning(f"Archivo vacío/no creado para '{voice_id}'.")
             if os.path.exists(output_path):
                 os.remove(output_path)
             return False
    except Exception as e:
        st.warning(f"Error generando parte con voz {voice_id}: {e}")
        return False

async def generate_full_audio(title_text, script, outro_text, outro_enabled, narrator_voices, narrator_speeds, progress_bar=None, progress_text=None):
    """Genera archivo de audio completo combinando partes."""
    temp_dir_obj = tempfile.TemporaryDirectory()
    temp_dir = temp_dir_obj.name
    segments = []
    total_steps = 0
    current_step = 0
    has_any_audio = False

    # Calcular pasos
    if title_text: total_steps += 1
    pattern = r'\[([^\]]+)\](.*?)(?=\n\[|\Z)'
    matches = re.findall(pattern, script, re.DOTALL)
    total_steps += len(matches)
    if outro_enabled and outro_text: total_steps += 1
    total_steps += 1 # Combinación

    def update_progress(step, message):
        progress = min(1.0, step / total_steps) if total_steps > 0 else 0
        if progress_bar: progress_bar.progress(progress)
        if progress_text: progress_text.text(f"({int(progress*100)}%) {message}")

    # Generar Título
    if title_text:
        current_step += 1
        update_progress(current_step, "Generando Título...")
        voice_id, speed = get_narrator_voice_settings(TITLE_NARRATOR_NAME, "male")
        if voice_id:
            title_file = os.path.join(temp_dir, "title_part.mp3")
            if await _generate_single_part(title_text.strip(), voice_id, speed, title_file):
                segments.append({"type": "audio", "path": title_file})
                if matches or (outro_enabled and outro_text):
                    segments.append({"type": "pause", "duration": PAUSE_BETWEEN_SECTIONS_MS})
                has_any_audio = True
        else:
            st.warning(f"No se pudo obtener voz para '{TITLE_NARRATOR_NAME}'. Saltando título.")

    # Generar Script
    for i, (narrator, text_part) in enumerate(matches):
        current_step += 1
        narrator = narrator.strip()
        text_part = text_part.strip()
        update_progress(current_step, f"Generando parte {i + 1}/{len(matches)} ({narrator})...")
        if text_part:
            voice_id, speed = get_narrator_voice_settings(narrator)
            if voice_id:
                 output_file = os.path.join(temp_dir, TEMP_AUDIO_FILE_PATTERN.format(i))
                 if await _generate_single_part(text_part, voice_id, speed, output_file):
                     if has_any_audio:
                         segments.append({"type": "crossfade", "duration": CROSSFADE_DURATION_MS})
                     segments.append({"type": "audio", "path": output_file})
                     has_any_audio = True
                 else:
                     st.warning(f"Fallo al generar audio para '{narrator}'. Saltando parte.")
            else:
                 st.warning(f"No se pudo obtener voz para '{narrator}'. Saltando parte.")
        else:
             st.info(f"Parte vacía para narrador '{narrator}'. Saltando.")

    # Generar Outro
    if outro_enabled and outro_text:
        current_step += 1
        update_progress(current_step, "Generando Outro...")
        if has_any_audio:
             segments.append({"type": "pause", "duration": PAUSE_BETWEEN_SECTIONS_MS})
        voice_id, speed = get_narrator_voice_settings(OUTRO_NARRATOR_NAME, "female")
        if voice_id:
            outro_file = os.path.join(temp_dir, "outro_part.mp3")
            if await _generate_single_part(outro_text.strip(), voice_id, speed, outro_file):
                if segments and segments[-1]["type"] == "pause" and len(segments) > 1:
                     segments.append({"type": "crossfade", "duration": CROSSFADE_DURATION_MS})
                segments.append({"type": "audio", "path": outro_file})
                has_any_audio = True
        else:
             st.warning(f"No se pudo obtener voz para '{OUTRO_NARRATOR_NAME}'. Saltando outro.")

    # Combinar
    current_step += 1
    audio_segment_paths = [s["path"] for s in segments if s['type'] == 'audio']
    if not audio_segment_paths:
        st.error("No se generó ningún segmento de audio válido para combinar.")
        update_progress(total_steps, "Error: No hay audio para combinar.")
        temp_dir_obj.cleanup()
        return None

    update_progress(current_step, f"Combinando {len(audio_segment_paths)} partes de audio...")
    combined_audio = AudioSegment.empty()
    last_audio_segment = None

    try:
        for idx, segment_info in enumerate(segments):
            segment_type = segment_info["type"]
            if segment_type == "audio":
                try:
                    current_segment = AudioSegment.from_file(segment_info["path"])
                    if last_audio_segment is not None and idx > 0 and segments[idx-1]["type"] == "crossfade":
                         cf_duration = segments[idx-1]["duration"]
                         safe_cf = min(cf_duration, len(last_audio_segment) // 2, len(current_segment) // 2)
                         if safe_cf > 10:
                              combined_audio = combined_audio.append(current_segment, crossfade=safe_cf)
                         else:
                              combined_audio += current_segment
                    else:
                         combined_audio += current_segment
                    last_audio_segment = current_segment
                except Exception as e_load:
                    st.warning(f"Error cargando segmento {segment_info['path']}: {e_load}. Saltando.")
                    continue
            elif segment_type == "pause":
                if len(combined_audio) > 0:
                    combined_audio += AudioSegment.silent(duration=segment_info["duration"])
                last_audio_segment = None

        if len(combined_audio) > 0:
            timestamp = st.session_state.last_run_timestamp
            output_filename = GENERATED_AUDIO_FILENAME.format(timestamp)
            output_path = Path(OUTPUT_SUBDIR) / output_filename
            combined_audio.export(output_path, format="mp3")
            update_progress(total_steps, "¡Audio combinado con éxito!")
            return str(output_path)
        else:
            st.error("Error: No se pudieron cargar los segmentos de audio generados.")
            update_progress(total_steps, "Error combinando audio.")
            return None
    except Exception as e:
        st.error(f"Error inesperado al combinar los archivos de audio: {e}")
        update_progress(total_steps, f"Error combinando audio: {e}")
        return None
    finally:
        temp_dir_obj.cleanup()

def detect_narrators(script_text):
    """Detecta nombres [Narrador] en el texto."""
    if not script_text: return []
    pattern = r'\[([^\]]+)\]'
    narrators = list(set(
        n.strip() for n in re.findall(pattern, script_text)
        if n.strip() and n.strip() not in [TITLE_NARRATOR_NAME, OUTRO_NARRATOR_NAME]
    ))
    return sorted(narrators)

def update_narrators_and_defaults():
    """Actualiza lista de narradores y asegura configs por defecto."""
    script_narrators = detect_narrators(st.session_state.get('script', ''))
    st.session_state.script_narrators = script_narrators

    base_narrators = []
    if st.session_state.get('title_text', ''): base_narrators.append(TITLE_NARRATOR_NAME)
    if st.session_state.get('outro_enabled', False) and st.session_state.get('outro_text', ''): base_narrators.append(OUTRO_NARRATOR_NAME)

    all_narrators = sorted(list(set(
        base_narrators + script_narrators + st.session_state.get('additional_narrators', [])
    )))

    for narrator in all_narrators:
        # Asignar Género default
        if narrator not in st.session_state.gender_selection:
            default_gender = "male" if narrator == TITLE_NARRATOR_NAME else "female"
            st.session_state.gender_selection[narrator] = default_gender

        # Asignar Voz/Velocidad default (si faltan)
        if narrator not in st.session_state.narrator_voices or \
           st.session_state.narrator_voices.get(narrator) is None or \
           narrator not in st.session_state.narrator_speeds or \
           st.session_state.narrator_speeds.get(narrator) is None:
            # Llamar a get_narrator_voice_settings fuerza la asignación
            _ = get_narrator_voice_settings(narrator, st.session_state.gender_selection.get(narrator, "female"))

# --- Callbacks de UI ---
def on_youtube_url_change():
    """Actualiza estado URL YouTube."""
    st.session_state.youtube_url = st.session_state.get("youtube_url_input", "")

def on_generate_prompt_change():
    """Actualiza estado prompt ChatGPT."""
    st.session_state.generate_prompt = st.session_state.get("generate_prompt_input", "")

def on_extract_youtube():
    """Callback botón 'Extraer y Procesar' YouTube."""
    url = st.session_state.get('youtube_url', '')
    if not url or not ("youtube.com" in url or "youtu.be" in url):
        st.error("URL de YouTube inválida.")
        return

    # Limpiar estados ANTES
    st.session_state.script = ""
    st.session_state.generated_content = None
    st.session_state.edited_content = ""
    st.session_state.gemini_result = None
    st.session_state.transcription_result = None
    st.session_state.edited_gemini_content = ""
    update_narrators_and_defaults()

    status = st.status("Procesando YouTube...", expanded=True)
    audio_path = None
    temp_dir_path = None
    try:
        # Usar la nueva función de descarga/extracción
        audio_path, temp_dir_path = download_youtube_video_and_extract_audio(url, status)
        if not audio_path:
            raise Exception("Fallo al obtener audio MP3 de YouTube.")

        # Usar la nueva función de transcripción con chunking
        transcript = transcribe_audio_whisper(audio_path, status)
        if transcript is None: # Vacío "" es OK, None indica error
            raise Exception("Fallo en transcripción Whisper.")
        st.session_state.transcription_result = transcript

        gemini_processed_text = process_with_gemini(transcript, status)
        if gemini_processed_text is None:
            raise Exception("Fallo en procesamiento Gemini.")

        st.session_state.gemini_result = gemini_processed_text
        st.session_state.edited_gemini_content = gemini_processed_text
        status.update(label="¡Proceso completado! Revisa y acepta el guión.", state="complete", expanded=False)

    except Exception as e:
        status.update(label=f"Error: {e}", state="error", expanded=True)
    finally:
        # Limpieza del directorio temporal (contiene MP3 si existe)
        if temp_dir_path and os.path.isdir(temp_dir_path):
            try:
                shutil.rmtree(temp_dir_path)
            except OSError as e_clean:
                print(f"Adv: No se pudo limpiar dir temp {temp_dir_path}: {e_clean}")

def on_accept_gemini_story():
    """Callback aceptar guión editado de Gemini."""
    st.session_state.script = st.session_state.get('edited_gemini_content_area', '')
    update_narrators_and_defaults()
    st.session_state.gemini_result = None # Ocultar editor
    st.session_state.edited_gemini_content = ""
    st.success("Guión (YouTube/Gemini) aceptado.")

def on_script_change():
    """Callback text_area manual."""
    if st.session_state.get('input_method') == "manual":
        st.session_state.script = st.session_state.get('script_content_manual', '')
        update_narrators_and_defaults()

def on_additional_narrators_change():
    """Actualiza lista de narradores adicionales."""
    narrator_str = st.session_state.get('narrator_input', '')
    st.session_state.additional_narrators = [n.strip() for n in narrator_str.split(",") if n.strip()]
    update_narrators_and_defaults()

def on_title_change():
    """Actualiza estado del título."""
    st.session_state.title_text = st.session_state.get("title_input", "")
    update_narrators_and_defaults()

def on_outro_change():
    """Actualiza estado texto outro."""
    st.session_state.outro_text = st.session_state.get("outro_input", "")
    update_narrators_and_defaults()

def on_outro_enable_change():
    """Actualiza estado habilitación outro."""
    st.session_state.outro_enabled = st.session_state.get("outro_checkbox", False)
    update_narrators_and_defaults()

def toggle_gender(narrator):
    """Cambia género y resetea voz/velocidad."""
    current_gender = st.session_state.gender_selection.get(narrator, "female")
    new_gender = "male" if current_gender == "female" else "female"
    st.session_state.gender_selection[narrator] = new_gender
    st.session_state.narrator_voices[narrator] = None
    st.session_state.narrator_speeds[narrator] = None
    update_narrators_and_defaults()

def save_voice_selection(narrator, voice_key):
    """Guarda voz seleccionada."""
    gender = st.session_state.gender_selection.get(narrator, "female")
    voices = FILTERED_VOICES.get(gender, {})
    if voice_key in voices:
        voice_info = voices[voice_key]
        st.session_state.narrator_voices[narrator] = voice_info
        # Si velocidad no definida, usar la de la voz
        if narrator not in st.session_state.narrator_speeds or st.session_state.narrator_speeds.get(narrator) is None:
             st.session_state.narrator_speeds[narrator] = voice_info.get("speed", DEFAULT_SPEED_SLIDER_VALUE)
    else:
        st.warning(f"Clave voz '{voice_key}' inválida {narrator} ({gender}). Resetando.")
        st.session_state.narrator_voices[narrator] = None
        st.session_state.narrator_speeds[narrator] = None
        update_narrators_and_defaults()

def save_speed_selection(narrator, speed):
    """Guarda velocidad seleccionada."""
    try:
        st.session_state.narrator_speeds[narrator] = float(speed)
    except (ValueError, TypeError):
        st.warning(f"Velocidad inválida '{speed}' para {narrator}. Usando default.")
        st.session_state.narrator_speeds[narrator] = DEFAULT_SPEED_SLIDER_VALUE

def on_generate_content_openai():
    """Callback botón 'Generar con ChatGPT'."""
    prompt = st.session_state.get('generate_prompt', '')
    option = st.session_state.get('generate_option', 'Historia')
    if not prompt:
        st.warning("Introduce un tema para ChatGPT.")
        return

    # Limpiar estados ANTES
    st.session_state.script = ""
    st.session_state.youtube_url = ""
    st.session_state.gemini_result = None
    st.session_state.edited_gemini_content = ""
    st.session_state.generated_content = None
    st.session_state.edited_content = ""
    update_narrators_and_defaults()

    with st.spinner("Generando con ChatGPT..."):
        generated = generate_with_openai(prompt, option)
        st.session_state.generated_content = generated
        st.session_state.edited_content = generated

def on_accept_openai_story():
    """Callback aceptar guión editado de ChatGPT."""
    st.session_state.script = st.session_state.get('edited_content_area', '')
    update_narrators_and_defaults()
    st.session_state.generated_content = None # Ocultar editor
    st.session_state.edited_content = ""
    st.success("Guión (ChatGPT) aceptado.")

# --- Funciones Video/Gestión Archivos ---
def delete_generated_video():
    """Elimina archivo de video generado."""
    path_str = st.session_state.get("generated_video_path")
    if path_str and Path(path_str).exists():
        try:
            os.remove(path_str)
            st.success(f"Video '{Path(path_str).name}' eliminado.")
            st.session_state.generated_video_path = None
            st.rerun() # Actualizar UI resultados
        except OSError as e:
            st.error(f"No se pudo eliminar video: {e}")
    else:
        if path_str: # Limpiar estado si el archivo no existe
            st.session_state.generated_video_path = None
        st.warning("No hay video generado para eliminar.")

def parse_duration_from_filename(filename):
    """Extrae duración HH_MM_SS_ del nombre y devuelve segundos."""
    match = re.match(VIDEO_FILENAME_PATTERN, filename)
    if match:
        try:
            return int(match.group(1))*3600 + int(match.group(2))*60 + int(match.group(3))
        except ValueError:
            return None
    return None

def find_suitable_video(target_duration_sec):
    """Encuentra video base aleatorio adecuado en duración."""
    suitable_videos = []
    if not VIDEO_SOURCE_FOLDER.is_dir():
        st.error(f"Carpeta videos base no encontrada: {VIDEO_SOURCE_FOLDER}")
        return None

    for item in VIDEO_SOURCE_FOLDER.iterdir():
        if item.is_file() and item.suffix.lower() == ".mp4":
            video_duration = parse_duration_from_filename(item.name)
            if video_duration is not None and video_duration >= target_duration_sec:
                suitable_videos.append(item)

    if not suitable_videos:
        st.warning(f"No hay videos base >= {target_duration_sec:.2f}s en '{VIDEO_SOURCE_FOLDER}'.")
        return None
    return random.choice(suitable_videos)

def create_video_with_audio(audio_path_str, video_filename_pattern, status_placeholder=None):
    """Crea video combinando audio y video base con FFmpeg."""
    audio_path = Path(audio_path_str)
    if not audio_path.exists():
        st.error(f"Audio no encontrado para crear video: {audio_path}")
        return None

    def update_status(message):
        if status_placeholder:
            status_placeholder.text(message)

    try:
        update_status("Calculando duración audio...")
        audio = AudioSegment.from_file(audio_path)
        audio_duration_sec = len(audio) / 1000.0
        update_status(f"Duración: {audio_duration_sec:.2f}s. Buscando video base...")

        video_source_path = find_suitable_video(audio_duration_sec)
        if not video_source_path:
            return None # Error ya mostrado

        update_status(f"Video base: {video_source_path.name}. Preparando FFmpeg...")
        timestamp = st.session_state.last_run_timestamp
        output_video_filename = video_filename_pattern.format(timestamp)
        output_video_path = Path(OUTPUT_SUBDIR) / output_video_filename

        ffmpeg_cmd = [
            "ffmpeg", "-i", str(video_source_path), "-i", str(audio_path),
            "-map", "0:v:0", "-map", "1:a:0", "-c:v", "copy", "-c:a", "aac",
            "-b:a", "192k", "-shortest", "-t", str(audio_duration_sec), "-y",
            str(output_video_path)
        ]

        update_status("Ejecutando FFmpeg (combinando audio y video)...")
        try:
            result = subprocess.run(ffmpeg_cmd, capture_output=True, text=True, check=True, encoding='utf-8', errors='ignore')
            if result.stderr and any(err in result.stderr.lower() for err in ["error", "fail", "invalid"]):
                 st.warning(f"FFmpeg reportó problemas:\n{result.stderr[:500]}...")
            update_status("¡Video generado con éxito!")
            return str(output_video_path)

        except FileNotFoundError:
            st.error("Error Crítico: FFmpeg no encontrado. Instálalo y asegúrate que esté en el PATH.")
            update_status("Error: FFmpeg no encontrado.")
            return None
        except subprocess.CalledProcessError as e:
            st.error(f"FFmpeg falló (código {e.returncode}):\n{e.stderr}")
            update_status("Error ejecutando FFmpeg.")
            return None

    except Exception as e:
        st.error(f"Error inesperado creando video: {e}")
        update_status(f"Error inesperado creando video: {e}")
        return None

# --- UI Principal (Layout y Widgets) ---
st.set_page_config(layout="wide", page_title="Narrador TTS Pro")
st.title("🎙️ Narrador TTS Pro: YouTube, IA y Video")

# CSS para video preview
st.markdown(f"""<style>.stVideo {{ max-width: {VIDEO_PREVIEW_WIDTH}px !important; margin-left: 0 !important; margin-right: auto !important; }}</style>""", unsafe_allow_html=True)

# --- Sección 1: Obtener Guión ---
st.subheader("1. Obtener el Guión")

# Radio button para método de entrada
input_options_map = {
    "Extraer de YouTube": "youtube",
    "Generar con ChatGPT": "chatgpt",
    "Introducir Manualmente": "manual"
}
option_labels = list(input_options_map.keys())
option_keys = list(input_options_map.values())

current_method_key = st.session_state.input_method
try:
    current_index = option_keys.index(current_method_key)
except ValueError:
    st.warning(f"Método inválido ('{current_method_key}') en estado. Volviendo a YouTube.")
    current_index = 0
    st.session_state.input_method = "youtube"

selected_label = st.radio(
    "Selecciona el método:",
    options=option_labels,
    key='input_method_radio',
    horizontal=True,
    index=current_index,
    label_visibility="collapsed"
)

# Lógica para actualizar estado y UI al cambiar método
new_method_key = input_options_map[selected_label]
if st.session_state.input_method != new_method_key:
    st.session_state.input_method = new_method_key
    # Limpiar estados de otros métodos
    if new_method_key != "youtube":
        st.session_state.gemini_result = None
        st.session_state.edited_gemini_content = ""
    if new_method_key != "chatgpt":
        st.session_state.generated_content = None
        st.session_state.edited_content = ""
    st.rerun() # Forzar re-ejecución para mostrar UI correcta

# Contenedor dinámico para la entrada
script_input_container = st.container()
with script_input_container:

    # UI: YouTube
    if st.session_state.input_method == "youtube":
        st.markdown("##### Extraer Guión desde YouTube")
        st.text_input(
            "URL del video:",
            placeholder="Pega la URL aquí...",
            key="youtube_url_input",
            value=st.session_state.youtube_url,
            on_change=on_youtube_url_change
        )
        extract_disabled = not bool(st.session_state.youtube_url)
        if st.button("🎤 Extraer y Procesar Guión YouTube", key="extract_youtube_btn", type="primary", disabled=extract_disabled):
            on_extract_youtube()

        # Editor para resultado Gemini
        if st.session_state.gemini_result is not None:
            st.info("Revisa y edita el guión procesado por Gemini:")
            edited_gemini_val = st.text_area(
                "Guión Procesado (Editable):",
                value=st.session_state.edited_gemini_content,
                height=SCRIPT_TEXT_AREA_HEIGHT + 70,
                key="edited_gemini_content_area"
            )
            # Actualizar estado editable directamente
            if edited_gemini_val != st.session_state.edited_gemini_content:
                 st.session_state.edited_gemini_content = edited_gemini_val

            if st.button("✅ Aceptar Guión (YouTube/Gemini)", on_click=on_accept_gemini_story, key="accept_gemini_btn", type="primary"):
                 pass # Lógica en callback

    # UI: ChatGPT
    elif st.session_state.input_method == "chatgpt":
        st.markdown("##### Generar Guión con ChatGPT")
        col1_gen, col2_gen = st.columns([3, 1])
        with col1_gen:
            st.text_input(
                "¿Sobre qué quieres el guión?:",
                placeholder="Ej: La historia de la IA",
                key="generate_prompt_input",
                value=st.session_state.generate_prompt,
                on_change=on_generate_prompt_change
            )
        with col2_gen:
            st.selectbox(
                "Tipo:",
                options=["Historia", "Curiosidades"],
                key="generate_option"
            )
        gen_openai_disabled = not bool(st.session_state.generate_prompt)
        if st.button("🤖 Generar Guión ChatGPT", on_click=on_generate_content_openai, key="generate_openai_btn", type="secondary", disabled=gen_openai_disabled):
            pass

        # Editor para resultado ChatGPT
        if st.session_state.generated_content is not None:
            st.info("Edita el contenido generado por ChatGPT:")
            edited_content_val = st.text_area(
                "Guión Generado (Editable):",
                value=st.session_state.edited_content,
                height=SCRIPT_TEXT_AREA_HEIGHT + 70,
                key="edited_content_area"
            )
            # Actualizar estado editable directamente
            if edited_content_val != st.session_state.edited_content:
                 st.session_state.edited_content = edited_content_val

            if st.button("✅ Aceptar Guión (ChatGPT)", on_click=on_accept_openai_story, key="accept_openai_btn", type="primary"):
                pass # Lógica en callback

    # UI: Manual
    elif st.session_state.input_method == "manual":
        st.markdown("##### Introducir Guión Manualmente")
        st.text_area(
            "Pega o escribe tu guión (formato [Narrador]):",
            height=SCRIPT_TEXT_AREA_HEIGHT,
            placeholder=SCRIPT_PLACEHOLDER,
            value=st.session_state.script,
            key="script_content_manual",
            on_change=on_script_change,
            help="Usa [Narrador] Texto..."
        )
        st.caption("Los cambios se guardan automáticamente.")

# --- Sección 2: Contenido Adicional ---
st.markdown("---")
st.subheader("2. Contenido Adicional (Opcional)")
st.text_input(
    "Título:",
    placeholder=TITLE_PLACEHOLDER,
    value=st.session_state.title_text,
    key="title_input",
    on_change=on_title_change
)
st.checkbox(
    "Añadir Outro",
    value=st.session_state.outro_enabled,
    key="outro_checkbox",
    on_change=on_outro_enable_change
)
if st.session_state.outro_enabled:
    st.text_input(
        "Texto del Outro:",
        placeholder=OUTRO_PLACEHOLDER,
        value=st.session_state.outro_text,
        key="outro_input",
        on_change=on_outro_change
    )

# --- Sección 3: Configuración Narradores ---
st.markdown("---")
st.subheader("3. Configuración Voces")
update_narrators_and_defaults() # Asegurar defaults

# Mostrar narradores detectados
if st.session_state.script:
    if st.session_state.script_narrators:
        st.success(f"Narradores detectados: {', '.join(st.session_state.script_narrators)}")
    else:
        st.warning("Guión cargado, pero sin etiquetas [Narrador] detectadas.")

# Narradores adicionales
st.text_input(
    "Narradores adicionales (separados por coma):",
    placeholder=NARRATOR_INPUT_PLACEHOLDER,
    value=", ".join(st.session_state.additional_narrators),
    key="narrator_input",
    on_change=on_additional_narrators_change
)

# Obtener lista final de narradores para UI
all_narrators_for_ui = sorted(list(set(
    ([TITLE_NARRATOR_NAME] if st.session_state.title_text else []) +
    ([OUTRO_NARRATOR_NAME] if st.session_state.outro_enabled and st.session_state.outro_text else []) +
    st.session_state.script_narrators +
    st.session_state.additional_narrators
)))

# UI para configurar voces
if all_narrators_for_ui:
    voice_container = st.container()
    with voice_container:
        st.markdown("---")
        num_cols = 2
        cols = st.columns(num_cols)
        col_idx = 0
        for i, narrator in enumerate(all_narrators_for_ui):
             # Validar config antes de renderizar
             if narrator not in st.session_state.narrator_voices or \
                st.session_state.narrator_voices.get(narrator) is None or \
                narrator not in st.session_state.narrator_speeds or \
                st.session_state.narrator_speeds.get(narrator) is None:
                  update_narrators_and_defaults() # Reintentar
                  if narrator not in st.session_state.narrator_voices or \
                     st.session_state.narrator_voices.get(narrator) is None or \
                     narrator not in st.session_state.narrator_speeds or \
                     st.session_state.narrator_speeds.get(narrator) is None:
                        with cols[col_idx % num_cols]:
                            st.error(f"Error config voz/vel para '{narrator}'.")
                        col_idx += 1
                        continue # Saltar narrador

             # Renderizar en columna
             with cols[col_idx % num_cols]:
                st.markdown(f"#### {narrator}")
                sub_col1, sub_col2 = st.columns([1, 3])

                # Col 1: Género y Muestra
                with sub_col1:
                    current_gender = st.session_state.gender_selection.get(narrator, "female")
                    st.radio(
                        "Género", options=["female", "male"],
                        format_func=lambda x: "F" if x == "female" else "M",
                        key=f"gender_{narrator}_{i}",
                        index=["female", "male"].index(current_gender),
                        horizontal=True, label_visibility="collapsed",
                        on_change=toggle_gender, args=(narrator,)
                    )
                    if st.button("▶️ Muestra", key=f"sample_{narrator}_{i}", help="Reproducir muestra"):
                        voice_info = st.session_state.narrator_voices[narrator]
                        speed_val = st.session_state.narrator_speeds[narrator]
                        voice_id = voice_info.get("id")
                        if voice_id:
                            with st.spinner("Generando muestra..."):
                                sample_audio = asyncio.run(generate_sample(voice_id, speed_val))
                                if sample_audio:
                                    st.audio(sample_audio, format="audio/mp3")
                        else:
                            st.warning("ID voz no encontrada.")

                # Col 2: Voz y Velocidad
                with sub_col2:
                    current_gender = st.session_state.gender_selection.get(narrator, "female")
                    voices_for_gender = FILTERED_VOICES.get(current_gender, {})
                    voice_keys = list(voices_for_gender.keys())

                    if voice_keys:
                        current_voice_info = st.session_state.narrator_voices.get(narrator)
                        try:
                            voice_index = [voices_for_gender[k] for k in voice_keys].index(current_voice_info)
                        except ValueError:
                             voice_index = 0
                             save_voice_selection(narrator, voice_keys[0]) # Forzar selección si no coincide

                        widget_key_voice = f"voice_selectbox_{narrator}_{i}_{current_gender}"
                        selected_voice_key = st.selectbox(
                            "Voz", options=voice_keys,
                            format_func=lambda k: voices_for_gender[k]["display"],
                            key=widget_key_voice, index=voice_index,
                            label_visibility="collapsed"
                        )
                        save_voice_selection(narrator, selected_voice_key) # Guardar tras renderizar

                        current_speed = st.session_state.narrator_speeds.get(narrator, DEFAULT_SPEED_SLIDER_VALUE)
                        widget_key_speed = f"speed_{narrator}_{i}"
                        selected_speed = st.slider(
                            "Velocidad", min_value=MIN_SPEED_VALUE, max_value=MAX_SPEED_VALUE,
                            value=float(current_speed), step=SPEED_STEP,
                            key=widget_key_speed, label_visibility="collapsed",
                            help=f"Velocidad: {current_speed:.1f}x"
                        )
                        save_speed_selection(narrator, selected_speed) # Guardar tras renderizar
                    else:
                        st.warning(f"No hay voces '{current_gender}'.")
                        st.session_state.narrator_voices[narrator] = None
                        st.session_state.narrator_speeds[narrator] = None

                st.markdown("---") # Separador entre narradores
                col_idx += 1
else:
    st.info("Acepta un guión o añade contenido/narradores para configurar voces.")

# --- Sección 4: Generación Final ---
st.markdown("---")
st.subheader("4. Generar Audio y Video Final")

generation_disabled = not bool(st.session_state.get('script', ''))
generation_tooltip = "Primero debes aceptar un guión." if generation_disabled else "Genera los archivos MP3 y MP4 finales"

if st.button("🚀 Generar Audio y Video", type="primary", key="generate_button", disabled=generation_disabled, help=generation_tooltip):

    if not st.session_state.script:
        st.error("Error: No hay guión cargado para generar.")
    else:
        st.session_state.generated_audio_path = None
        st.session_state.generated_video_path = None
        st.session_state.last_run_timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")

        progress_container = st.container()
        results_container = st.container()
        final_audio_path = None
        final_video_path = None
        audio_success = False
        video_success = False

        with progress_container:
            st.info("Iniciando proceso de generación...")
            audio_progress_bar = st.progress(0.0)
            audio_progress_text = st.empty()
            video_progress_text = st.empty()

            # Generación Audio
            with st.spinner("Generando audio..."):
                audio_progress_text.text("Preparando audio...")
                try:
                    update_narrators_and_defaults() # Asegurar configs
                    final_audio_path = asyncio.run(generate_full_audio(
                        st.session_state.title_text, st.session_state.script, st.session_state.outro_text,
                        st.session_state.outro_enabled, st.session_state.narrator_voices, st.session_state.narrator_speeds,
                        audio_progress_bar, audio_progress_text
                    ))
                    if final_audio_path and Path(final_audio_path).exists():
                        st.session_state.generated_audio_path = final_audio_path
                        audio_success = True
                    else:
                        audio_progress_text.error("Fallo generación archivo audio.")
                except Exception as e_audio:
                    audio_progress_text.error(f"Error crítico durante generación audio: {e_audio}")
                finally:
                    audio_progress_bar.progress(1.0) # Completar barra

            # Generación Video (si audio OK)
            if audio_success:
                with st.spinner("Generando video..."):
                    video_progress_text.text("Iniciando generación de video...")
                    try:
                        final_video_path = create_video_with_audio(
                            final_audio_path, GENERATED_VIDEO_FILENAME, video_progress_text
                        )
                        if final_video_path and Path(final_video_path).exists():
                            st.session_state.generated_video_path = final_video_path
                            video_success = True
                        else:
                            video_progress_text.warning("No se pudo generar el archivo de video.")
                    except Exception as e_video:
                        video_progress_text.error(f"Error crítico durante creación video: {e_video}")

        # Mostrar Resultados
        with results_container:
            st.markdown("---")
            st.subheader("Resultados Generados")
            res_col1, res_col2 = st.columns(2)

            # Columna Audio
            with res_col1:
                st.markdown("##### Audio (.mp3)")
                audio_path = st.session_state.generated_audio_path
                if audio_success and audio_path:
                    try:
                        with open(audio_path, "rb") as f:
                            audio_bytes = f.read()
                        st.audio(audio_bytes, format="audio/mp3")
                        st.download_button(
                            "⬇️ Descargar Audio", audio_bytes,
                            Path(audio_path).name, "audio/mp3", key="dl_audio"
                        )
                    except Exception as e:
                        st.error(f"Error leer/mostrar audio: {e}")
                        st.session_state.generated_audio_path = None
                elif not audio_success:
                    st.error("La generación del audio falló.")
                else: # Placeholder (should not be reached in normal flow)
                    st.info("Audio aparecerá aquí.")

            # Columna Video
            with res_col2:
                st.markdown("##### Video (.mp4)")
                video_path = st.session_state.generated_video_path
                if video_success and video_path:
                    try:
                        with open(video_path, "rb") as f:
                            video_bytes = f.read()
                        st.video(video_bytes, format="video/mp4")
                        btn_col1, btn_col2 = st.columns(2)
                        with btn_col1:
                            st.button("🗑️ Eliminar Video", key="del_vid", on_click=delete_generated_video, type="secondary")
                        with btn_col2:
                            st.button("✅ Guardado", key="save_vid", help=f"En carpeta '{OUTPUT_SUBDIR}'", disabled=True)
                        st.download_button(
                            "⬇️ Descargar Video", video_bytes,
                            Path(video_path).name, "video/mp4", key="dl_vid"
                        )
                    except Exception as e:
                        st.error(f"Error leer/mostrar video: {e}")
                        if Path(video_path).exists():
                            st.button("🗑️ Eliminar Video Dañado", key="del_bad_vid", on_click=delete_generated_video, type="secondary")
                        st.session_state.generated_video_path = None
                elif audio_success and not video_success:
                    st.warning("Audio generado, pero la creación del video falló.")
                elif not audio_success:
                    st.info("Video no generado (audio falló).")
                else: # Placeholder
                    st.info("Video aparecerá aquí.")

# Mostrar resultados previos si existen (y no se acaba de generar)
elif not st.session_state.get("generate_button", False) and \
     (st.session_state.generated_audio_path or st.session_state.generated_video_path):

     st.markdown("---")
     st.subheader("Resultados Anteriores")
     res_col1_prev, res_col2_prev = st.columns(2)

     # Columna Audio Previo
     with res_col1_prev:
        st.markdown("##### Audio (.mp3)")
        prev_audio_path = st.session_state.generated_audio_path
        if prev_audio_path and Path(prev_audio_path).exists():
            try:
                with open(prev_audio_path, "rb") as f:
                    audio_bytes = f.read()
                st.audio(audio_bytes, format="audio/mp3")
                st.download_button(
                    "⬇️ Descargar Audio", audio_bytes,
                    Path(prev_audio_path).name, "audio/mp3", key="dl_prev_audio"
                )
            except Exception as e:
                 st.error(f"Error cargar audio previo: {e}")
                 st.session_state.generated_audio_path = None # Resetear si hay error
        else:
            if prev_audio_path: # Limpiar estado si archivo no existe
                st.session_state.generated_audio_path = None
            st.info("No hay audio previo disponible.")

     # Columna Video Previo
     with res_col2_prev:
        st.markdown("##### Video (.mp4)")
        prev_video_path = st.session_state.generated_video_path
        if prev_video_path and Path(prev_video_path).exists():
            try:
                with open(prev_video_path, "rb") as f:
                    video_bytes = f.read()
                st.video(video_bytes, format="video/mp4")
                btn_col1p, btn_col2p = st.columns(2)
                with btn_col1p:
                    st.button("🗑️ Eliminar Video", key="del_prev_vid", on_click=delete_generated_video, type="secondary")
                with btn_col2p:
                    st.button("✅ Guardado", key="save_prev_vid", help=f"En {prev_video_path}", disabled=True)
                st.download_button(
                    "⬇️ Descargar Video", video_bytes,
                    Path(prev_video_path).name, "video/mp4", key="dl_prev_vid"
                )
            except Exception as e:
                 st.error(f"Error cargar video previo: {e}")
                 if Path(prev_video_path).exists():
                     st.button("🗑️ Eliminar Video Dañado", key="del_bad_prev_vid", on_click=delete_generated_video, type="secondary")
                 st.session_state.generated_video_path = None # Resetear si hay error
        else:
             if prev_video_path: # Limpiar estado si archivo no existe
                 st.session_state.generated_video_path = None
             st.info("No hay video previo disponible.")

# --- Fin del Script ---