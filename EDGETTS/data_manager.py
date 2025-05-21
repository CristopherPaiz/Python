# -*- coding: utf-8 -*-
import os
import json
import time
import pandas as pd

# Ruta al archivo JSON predeterminado
DEFAULT_JSON_PATH = os.path.join(os.path.dirname(__file__), "audio.json")

# Tipos válidos para el selector de tipo de contenido
TIPOS_CONTENIDO = ["Historia", "Resumen", "Cuento", "Fantasía", "Chisme", "Curiosidades", "Datos"]

def inicializar_tabla():
    """Inicializa la tabla con datos del archivo audio.json o con datos de ejemplo si no existe"""
    try:
        # Intentar cargar desde audio.json
        if os.path.exists(DEFAULT_JSON_PATH):
            with open(DEFAULT_JSON_PATH, 'r', encoding='utf-8') as f:
                datos_json = json.load(f)
                print(f"Archivo {DEFAULT_JSON_PATH} cargado correctamente.")
                
                # Asegurar que los datos existentes tengan los nuevos campos
                for item in datos_json:
                    if "tipo" not in item:
                        item["tipo"] = "Historia"  # Valor por defecto
                    if "etiquetas" not in item:
                        item["etiquetas"] = ""
                
                return pd.DataFrame(datos_json)
        else:
            print(f"Archivo {DEFAULT_JSON_PATH} no encontrado. Inicializando con datos de ejemplo.")
    except Exception as e:
        print(f"Error al cargar {DEFAULT_JSON_PATH}: {str(e)}. Inicializando con datos de ejemplo.")
    
    # Datos de ejemplo si no se pudo cargar el archivo
    data = [
        {
            "series": "Mi novio me engaño con la perra de mi tía",
            "seed": "random",
            "part": "4",
            "IA": True,
            "outro": "Sígueme para más historias completas",
            "text": "",
            "textAI": "Mi novio me engaño con la perra de mi tía",
            "randomVideo": False,
            "video": "",
            "tipo": "Historia",
            "etiquetas": "engaño,relaciones,drama"
        },
        {
            "series": "Titulo de la serie",
            "seed": "0",
            "part": "4",
            "IA": False,
            "outro": "Sígueme para más historias completas",
            "text": "texto variado que no genera la IA sino que se toma del texto",
            "textAI": "",
            "randomVideo": True,
            "video": "",
            "tipo": "Curiosidades",
            "etiquetas": "datos,información"
        }
    ]
    
    return pd.DataFrame(data)

def dataframe_a_json(df):
    """Convierte un DataFrame a formato JSON"""
    # Convertir tipos de datos para asegurar compatibilidad JSON
    df_copy = df.copy()
    
    # Convertir booleanos representados como strings a booleanos reales
    for col in ['IA', 'randomVideo']:
        if col in df_copy.columns:
            df_copy[col] = df_copy[col].apply(lambda x: x == 'True' if isinstance(x, str) else bool(x))
    
    # Convertir a lista de diccionarios (formato JSON)
    return df_copy.to_dict('records')

def guardar_json_auto(df):
    """Guarda automáticamente el dataframe en el archivo audio.json"""
    try:
        datos_json = dataframe_a_json(df)
        
        # Asegurar que el directorio existe
        directorio = os.path.dirname(DEFAULT_JSON_PATH)
        if directorio and not os.path.exists(directorio):
            os.makedirs(directorio)
            
        # Guardar con codificación UTF-8
        with open(DEFAULT_JSON_PATH, 'w', encoding='utf-8') as f:
            json.dump(datos_json, f, indent=4, ensure_ascii=False)
        
        mensaje = f"Datos guardados correctamente en {DEFAULT_JSON_PATH}"
        print(mensaje)
        return mensaje
    except Exception as e:
        error = f"Error al guardar en {DEFAULT_JSON_PATH}: {str(e)}"
        print(error)
        return error

def cargar_json(archivo_json):
    """Carga datos desde un archivo JSON subido"""
    try:
        if archivo_json is None:
            return inicializar_tabla(), "No se seleccionó ningún archivo"
            
        contenido = archivo_json.read().decode('utf-8')
        datos_json = json.loads(contenido)
        
        # Asegurar que los datos cargados tengan los nuevos campos
        for item in datos_json:
            if "tipo" not in item:
                item["tipo"] = "Historia"  # Valor por defecto
            if "etiquetas" not in item:
                item["etiquetas"] = ""
                
        df = pd.DataFrame(datos_json)
        guardar_json_auto(df)  # Guardar en el archivo predeterminado
        return df, f"Archivo JSON cargado correctamente con {len(df)} entradas"
    except Exception as e:
        return inicializar_tabla(), f"Error al cargar archivo JSON: {str(e)}"

def guardar_json(df):
    """Convierte el DataFrame a formato JSON para descarga"""
    try:
        datos_json = dataframe_a_json(df)
        # También guardar automáticamente en el archivo predeterminado
        guardar_json_auto(df)
        return datos_json, json.dumps(datos_json, indent=4, ensure_ascii=False)
    except Exception as e:
        error_msg = f"Error: {str(e)}"
        return None, error_msg

def crear_archivo_json(texto_json):
    """Crea un archivo JSON descargable"""
    try:
        if not texto_json:
            return None
            
        nombre_archivo = f"datos_audio_{int(time.time())}.json"
        with open(nombre_archivo, "w", encoding="utf-8") as f:
            f.write(texto_json)
        return nombre_archivo
    except Exception as e:
        print(f"Error al crear archivo JSON para descargar: {e}")
        return None

def on_table_change(df):
    """Maneja los cambios en la tabla y los guarda automáticamente"""
    mensaje = guardar_json_auto(df)
    return df, mensaje

def agregar_fila(df):
    """Agrega una fila vacía al DataFrame"""
    nueva_fila = pd.DataFrame([{
        "series": "",
        "seed": "random",
        "part": "1",
        "IA": False,
        "outro": "",
        "text": "",
        "textAI": "",
        "randomVideo": False,
        "video": "",
        "tipo": "Historia",
        "etiquetas": ""
    }])
    df_nuevo = pd.concat([df, nueva_fila], ignore_index=True)
    guardar_json_auto(df_nuevo)
    return df_nuevo, f"Nueva fila agregada. Total: {len(df_nuevo)} filas"