import whisperx
import gc
import os
import time
import re

# =========== PARÁMETROS CONFIGURABLES ===========
# Ruta del archivo de audio a transcribir
ARCHIVO_AUDIO = r"C:/Users/crist/OneDrive/Documents/Progra/Python/NewEdgeTTS/audios/narration.mp3"

# Modelo a utilizar (tiny, base, small, medium, large-v2, large-v3)
# Para mejor precisión en los tiempos, usar large-v2
MODELO = "large-v2"

# Idioma (es, en, etc.) - None para detección automática
IDIOMA = "es"

# Alineamiento a nivel de palabra (requerido para karaoke)
ALINEAMIENTO_PALABRAS = True

# Guardar resultado
GUARDAR_RESULTADO = True

# Tamaño de lote (reducir si hay problemas de memoria)
TAMANO_LOTE = 4

# Tipo de cómputo (float16 para mejor precisión, int8 para menor uso de memoria)
TIPO_COMPUTO = "int8"

# Máximo de caracteres por línea antes de dividir
MAX_CARACTERES_POR_LINEA = 30

# Ajuste de tiempo (en segundos) - Usa valores negativos para adelantar, positivos para retrasar
AJUSTE_TIEMPO = 0.0

# Configuración de video
VIDEO_WIDTH = 1080   # Ancho para formato vertical
VIDEO_HEIGHT = 1920  # Alto para formato vertical

# Colores para el karaoke (formato ASS: &HBBGGRR&)
COLOR_DEFAULT = "&HFFFFFF&"  # Blanco
COLOR_HIGHLIGHT = "&H00FFFF&"  # Amarillo
COLOR_OUTLINE = "&H000000&"  # Negro (para contorno)

# Fuente
FONT_NAME = "Arial"
FONT_SIZE = 65
OUTLINE_SIZE = 1

# Ajustes específicos para mejorar precisión de tiempo en WhisperX
USE_VAD = True           # Usar detección de actividad de voz para mejor precisión
EXTEND_DURATION = 0.02   # Extender ligeramente la duración de palabras para mejorar visibilidad
# ================================================

def format_ass_time(seconds):
    """
    Convierte segundos a formato de tiempo ASS (h:mm:ss.cc) con precisión mejorada
    """
    # Aplicar ajuste de tiempo si está configurado
    seconds = max(0, seconds + AJUSTE_TIEMPO)
    
    hours = int(seconds / 3600)
    minutes = int((seconds % 3600) / 60)
    seconds_part = seconds % 60
    centiseconds = int((seconds_part - int(seconds_part)) * 100)
    return f"{hours}:{minutes:02d}:{int(seconds_part):02d}.{centiseconds:02d}"

def parse_transcription_file(file_path):
    """
    Lee un archivo de transcripción previamente generado y construye una estructura
    similar a la que devuelve WhisperX para generar el archivo ASS.
    
    Returns:
        dict: Estructura de datos con segmentos y palabras alineadas
    """
    segments = []
    current_segment = None
    
    with open(file_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()
        
        # Omitir las primeras líneas con información del archivo
        start_line = 0
        for i, line in enumerate(lines):
            if line.strip() == "":
                start_line = i + 1
                break
        
        # Extraer segmentos y palabras
        i = start_line
        while i < len(lines):
            line = lines[i].strip()
            
            # Detectar línea de segmento: [0.21s -> 4.51s] texto
            segment_match = re.match(r'\[(\d+\.\d+)s -> (\d+\.\d+)s\](.*)', line)
            if segment_match:
                # Si ya teníamos un segmento, lo guardamos antes de comenzar uno nuevo
                if current_segment:
                    segments.append(current_segment)
                
                start_time = float(segment_match.group(1))
                end_time = float(segment_match.group(2))
                text = segment_match.group(3).strip()
                
                current_segment = {
                    "start": start_time,
                    "end": end_time,
                    "text": text,
                    "words": []
                }
                
                # Avanzar a la siguiente línea para buscar palabras
                i += 1
                
                # Extraer palabras de las siguientes líneas
                while i < len(lines) and lines[i].strip() and '-> ' in lines[i]:
                    word_line = lines[i].strip()
                    word_match = re.match(r'\s*\[(\d+\.\d+)s -> (\d+\.\d+)s\]: (.*)', word_line)
                    if word_match:
                        word_start = float(word_match.group(1))
                        word_end = float(word_match.group(2))
                        word_text = word_match.group(3).strip()
                        
                        current_segment["words"].append({
                            "start": word_start,
                            "end": word_end,
                            "word": word_text
                        })
                    
                    i += 1
            else:
                i += 1
        
        # Añadir el último segmento si existe
        if current_segment:
            segments.append(current_segment)
    
    # Obtener duración total
    duracion_total = max([s["end"] for s in segments]) if segments else 0
    
    return {
        "segments": segments,
        "duracion_total": duracion_total
    }

def generate_ass_styles(max_lines=8):
    """
    Genera los estilos ASS para múltiples líneas.
    
    Args:
        max_lines: Número máximo de líneas a soportar (por defecto 8)
    
    Returns:
        str: Sección de estilos para el archivo ASS
    """
    styles = """Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
"""
    
    # Calcular la posición central para el video vertical
    center_y = VIDEO_HEIGHT // 2
    line_height = 80  # Altura aproximada por línea (depende del tamaño de fuente)
    
    # Para cada posible número de líneas (de 1 a max_lines)
    for num_lines in range(1, max_lines + 1):
        # Calcular el desplazamiento inicial para centrar el grupo de líneas
        initial_offset = center_y - (num_lines * line_height) // 2
        
        # Para cada línea en el grupo
        for line_index in range(1, num_lines + 1):
            margin_v = initial_offset + (line_index - 1) * line_height
            style_name = f"Default{num_lines}{line_index}"
            styles += f"Style: {style_name},{FONT_NAME},{FONT_SIZE},&H00FFFFFF,&H000000FF,{COLOR_OUTLINE},&H80000000,-1,0,0,0,100,100,0,0,1,{OUTLINE_SIZE},2,8,10,10,{margin_v},1\n"
            
        # Separador entre grupos de líneas
        styles += f"Style: *********,{FONT_NAME},{FONT_SIZE},&H00FFFFFF,&H000000FF,{COLOR_OUTLINE},&H00000000,-1,0,0,0,100,100,0,0,1,{OUTLINE_SIZE},2,8,10,10,00000000,1\n"
    
    return styles

def process_segment_multiline(segment):
    """
    Procesa un segmento mostrando TODAS las líneas simultáneamente.
    Mantiene las etiquetas de tiempo básicas de karaoke sin efectos especiales.
    """
    if "words" not in segment or not segment["words"]:
        # Si no hay palabras alineadas, devolver una sola línea sin karaoke
        start_str = format_ass_time(segment["start"])
        end_str = format_ass_time(segment["end"])
        return [f'Dialogue: 0,{start_str},{end_str},Default11,,0,0,0,,{segment["text"]}']
    
    # Tiempos del segmento completo
    start_str = format_ass_time(segment["start"])
    end_str = format_ass_time(segment["end"])
    segment_start = segment["start"]
    words = segment["words"]
    
    # Agrupar palabras en líneas según el límite de caracteres
    lines = []
    current_line = []
    current_line_length = 0
    
    for word in words:
        word_text = word["word"].strip()
        word_length = len(word_text) + 1  # +1 para el espacio
        
        if current_line_length + word_length > MAX_CARACTERES_POR_LINEA and current_line:
            # Si agregar esta palabra excede el límite, cerramos la línea actual
            lines.append(current_line)
            current_line = [word]
            current_line_length = word_length
        else:
            # Agregamos la palabra a la línea actual
            current_line.append(word)
            current_line_length += word_length
    
    # Añadir la última línea si tiene contenido
    if current_line:
        lines.append(current_line)
    
    # Si hay demasiadas líneas, combinar algunas para no exceder el límite
    MAX_SUPPORTED_LINES = 8
    if len(lines) > MAX_SUPPORTED_LINES:
        # Estrategia simple: combinar las líneas extras con la última línea
        for i in range(MAX_SUPPORTED_LINES, len(lines)):
            lines[MAX_SUPPORTED_LINES-1].extend(lines[i])
        lines = lines[:MAX_SUPPORTED_LINES]
    
    # Generar las líneas de diálogo ASS - TODAS con el mismo tiempo de inicio/fin
    result_lines = []
    style_prefix = f"Default{len(lines)}"
    
    for i, line_words in enumerate(lines):
        # Estilo para esta línea
        style = f"{style_prefix}{i+1}"
        
        # Construir línea con karaoke básico (solo etiquetas de tiempo)
        karaoke_line = ""
        
        # Si es la primera palabra de la línea, calcular tiempo desde inicio del segmento
        first_word_start = line_words[0]["start"]
        initial_delay = max(0, int((first_word_start - segment_start) * 100))
        if initial_delay > 0:
            karaoke_line += f"{{\\k{initial_delay}}}"
        
        prev_end_time = first_word_start
        
        for j, word in enumerate(line_words):
            word_text = word["word"].strip()
            
            # Calcular tiempo de espera antes de esta palabra (silencio/pausa)
            wait_time = max(0, int((word["start"] - prev_end_time) * 100))
            if wait_time > 0:
                karaoke_line += f"{{\\k{wait_time}}}"
            
            # Calcular duración de la palabra y usar solo etiquetas básicas de tiempo
            word_duration = max(10, int((word["end"] - word["start"]) * 100))
            karaoke_line += f"{{\\k{word_duration}}}{word_text}"
            
            # Añadir espacio después de cada palabra (excepto la última)
            if j < len(line_words) - 1:
                karaoke_line += " "
            
            # Actualizar el tiempo de fin anterior para la próxima palabra
            prev_end_time = word["end"]
        
        # Añadir la línea al resultado - TODAS con mismo tiempo de inicio/fin
        result_lines.append(f'Dialogue: 0,{start_str},{end_str},{style},,0,0,0,,{karaoke_line}')
    
    return result_lines

def generate_ass_karaoke_multiline(resultado, output_file, audio_duration):
    """
    Genera un archivo de subtítulos ASS con timing de karaoke para cada palabra,
    soportando múltiples líneas por segmento.
    
    Args:
        resultado: Resultado de transcripción de WhisperX con alineación de palabras
        output_file: Ruta del archivo ASS de salida
        audio_duration: Duración del audio en segundos
    """
    # Plantilla de encabezado de archivo ASS
    header = f"""[Script Info]
; Script generated by WhisperX Karaoke Basic
; Username: {os.environ.get('USERNAME', 'CristopherPaiz')}
; Date: {time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())}
Title: Karaoke Transcription
ScriptType: v4.00+
WrapStyle: 0
ScaledBorderAndShadow: yes
YCbCr Matrix: TV.601
PlayResX: {VIDEO_WIDTH}
PlayResY: {VIDEO_HEIGHT}

[Aegisub Project Garbage]
Audio File: {ARCHIVO_AUDIO}
Video File: ?dummy:23.976000:40000:1080:1920:47:163:254:
Video AR Mode: 4
Video AR Value: {VIDEO_WIDTH / VIDEO_HEIGHT:.6f}
Video Zoom Percent: 0.500000
Scroll Position: 0
Active Line: 0
Video Position: 0

[V4+ Styles]
"""

    with open(output_file, "w", encoding="utf-8") as f:
        f.write(header)
        f.write(generate_ass_styles())
        f.write("\n[Events]\n")
        f.write("Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text\n")
        
        # Procesar cada segmento
        for segment in resultado["segments"]:
            for line in process_segment_multiline(segment):
                f.write(f"{line}\n")
    
    print(f"✅ Archivo de subtítulos ASS con timing de karaoke básico generado: {output_file}")

def main():
    try:
        inicio_tiempo = time.time()
        
        print("\n=== TRANSCRIPCIÓN CON WHISPERX Y GENERACIÓN DE KARAOKE BÁSICO ===")
        print(f"Modelo: {MODELO} | Tipo de cómputo: {TIPO_COMPUTO}")
        
        # Verificar que el archivo exista
        if not os.path.exists(ARCHIVO_AUDIO):
            print(f"❌ Error: El archivo {ARCHIVO_AUDIO} no existe")
            return
            
        print(f"Archivo de audio: {os.path.basename(ARCHIVO_AUDIO)}")
        
        # Verificar si ya existe un archivo de transcripción
        archivo_transcripcion = os.path.splitext(ARCHIVO_AUDIO)[0] + "_transcripcion.txt"
        transcripcion_existe = os.path.exists(archivo_transcripcion)
        
        if transcripcion_existe:
            print(f"🔍 Se encontró un archivo de transcripción existente: {os.path.basename(archivo_transcripcion)}")
            print("⚙️ Cargando transcripción existente...")
            
            # Cargar datos desde el archivo de transcripción
            datos_cargados = parse_transcription_file(archivo_transcripcion)
            resultado = datos_cargados
            duracion_total = datos_cargados["duracion_total"]
            
            print(f"✅ Transcripción cargada: {len(resultado['segments'])} segmentos, {duracion_total:.2f} segundos")
            
        else:
            print("🔍 No se encontró un archivo de transcripción existente. Procediendo a transcribir...")
            
            # Cargar modelo con mejor precisión
            print(f"⚙️ Cargando modelo {MODELO} en modo {TIPO_COMPUTO}...")
            modelo = whisperx.load_model(
                MODELO, 
                "cpu", 
                compute_type=TIPO_COMPUTO, 
                language=IDIOMA
            )
            print("✅ Modelo cargado correctamente")
            
            # Cargar audio
            print("⚙️ Cargando audio...")
            audio = whisperx.load_audio(ARCHIVO_AUDIO)
            duracion_audio = len(audio)/16000
            print(f"✅ Audio cargado: {duracion_audio:.2f} segundos")
            
            # Transcribir con parámetros compatibles con tu versión de WhisperX
            print("⚙️ Transcribiendo audio...")
            resultado = modelo.transcribe(
                audio, 
                batch_size=TAMANO_LOTE,
                print_progress=True
            )
            print("✅ Transcripción completada")
            
            # Guardar el idioma detectado antes del alineamiento
            idioma_detectado = resultado.get("language", "desconocido")
            print(f"🔍 Idioma detectado: {idioma_detectado}")
            
            # Liberar memoria
            del modelo
            gc.collect()
            
            # Alineamiento de palabras con máxima precisión
            print("⚙️ Cargando modelo de alineamiento para mayor precisión de palabras...")
            modelo_alineamiento, metadata = whisperx.load_align_model(
                language_code=idioma_detectado, 
                device="cpu"
            )
            
            print("⚙️ Realizando alineamiento de palabras de alta precisión...")
            try:
                # Intentar con todos los parámetros de alta precisión
                resultado_alineado = whisperx.align(
                    resultado["segments"],
                    modelo_alineamiento, 
                    metadata, 
                    audio, 
                    "cpu",
                    return_char_alignments=False,
                    interpolate_method="linear",
                    extend_duration=0.01
                )
            except TypeError:
                # Si falla, intentar con parámetros básicos
                print("⚠️ Usando parámetros básicos de alineamiento...")
                resultado_alineado = whisperx.align(
                    resultado["segments"],
                    modelo_alineamiento, 
                    metadata, 
                    audio, 
                    "cpu",
                    return_char_alignments=False
                )
            
            # Actualizar resultado
            resultado = resultado_alineado
            print("✅ Alineamiento completado")
            
            # Refinar tiempos de palabras (post-procesamiento)
            print("⚙️ Refinando tiempos de palabras...")
            # Asegurar que las palabras no se sobrepongan
            for segmento in resultado["segments"]:
                if "words" in segmento and len(segmento["words"]) > 1:
                    palabras = segmento["words"]
                    for i in range(1, len(palabras)):
                        # Si la palabra actual empieza antes de que termine la anterior
                        if palabras[i]["start"] < palabras[i-1]["end"]:
                            # Ajustar para que empiece justo cuando termina la anterior
                            palabras[i]["start"] = palabras[i-1]["end"]
            
            # Liberar memoria
            del modelo_alineamiento
            gc.collect()
            
            # Mostrar resultados
            print("\n=== RESULTADOS DE TRANSCRIPCIÓN ===")
            
            # Calcular estadísticas
            total_segmentos = len(resultado["segments"])
            duracion_total = max([s["end"] for s in resultado["segments"]])
            total_palabras = sum([len(s.get("words", [])) for s in resultado["segments"]])
            
            print(f"Total segmentos: {total_segmentos}")
            print(f"Total palabras alineadas: {total_palabras}")
            print(f"Duración total: {duracion_total:.2f} segundos")
            
            # Mostrar primeros segmentos
            max_mostrar = min(3, total_segmentos)
            print(f"\nPrimeros {max_mostrar} segmentos:")
            for i, segmento in enumerate(resultado["segments"][:max_mostrar]):
                print(f"\nSegmento {i+1} [{segmento['start']:.2f}s -> {segmento['end']:.2f}s]")
                print(f"Texto: {segmento['text']}")
                
                if "words" in segmento and segmento["words"]:
                    palabras_muestra = segmento["words"][:5]
                    print("Palabras:")
                    for palabra in palabras_muestra:
                        print(f"  [{palabra['start']:.2f}s -> {palabra['end']:.2f}s]: {palabra['word']}")
                    
                    if len(segmento["words"]) > 5:
                        print(f"  ... y {len(segmento['words']) - 5} palabras más")
            
            # Guardar resultado de transcripción
            if GUARDAR_RESULTADO and not transcripcion_existe:
                # Guardar transcripción de texto
                with open(archivo_transcripcion, "w", encoding="utf-8") as f:
                    f.write(f"Transcripción de: {os.path.basename(ARCHIVO_AUDIO)}\n")
                    f.write(f"Modelo: {MODELO}\n")
                    f.write(f"Idioma: {idioma_detectado}\n")
                    f.write(f"Duración: {duracion_total:.2f} segundos\n\n")
                    
                    # Escribir segmentos
                    for i, segmento in enumerate(resultado["segments"]):
                        f.write(f"\n[{segmento['start']:.2f}s -> {segmento['end']:.2f}s] {segmento['text']}\n")
                        
                        if "words" in segmento and segmento["words"]:
                            for palabra in segmento["words"]:
                                f.write(f"  [{palabra['start']:.2f}s -> {palabra['end']:.2f}s]: {palabra['word']}\n")
                
                print(f"\n✅ Transcripción guardada en: {os.path.basename(archivo_transcripcion)}")
        
        # Generar archivo ASS de karaoke multi-línea básico
        archivo_salida_ass = os.path.splitext(ARCHIVO_AUDIO)[0] + "_karaoke_basico.ass"
        generate_ass_karaoke_multiline(resultado, archivo_salida_ass, duracion_total if 'duracion_total' in locals() else resultado["duracion_total"])
        print(f"\n✅ Archivo de subtítulos ASS con karaoke básico generado: {os.path.basename(archivo_salida_ass)}")
        
        # Mostrar instrucciones para ajustar tiempo si es necesario
        print("\n📌 INSTRUCCIONES DE USO:")
        print("   - Si notas desincronización, ajusta AJUSTE_TIEMPO (- para adelantar, + para retrasar)")
        
        # Mostrar tiempo total
        tiempo_total = time.time() - inicio_tiempo
        print(f"\n⏱️ Tiempo total: {tiempo_total:.1f} segundos")
        
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()