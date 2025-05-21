# -*- coding: utf-8 -*-
import os
from dotenv import load_dotenv

# Cargar variables de entorno si no se ha hecho
load_dotenv()

# Cliente global de OpenAI
client = None

def inicializar_openai_client(api_key=None):
    """Inicializa el cliente de OpenAI con una clave API proporcionada"""
    global client
    try:
        from openai import OpenAI
        
        # Prioridad: 1. API key proporcionada, 2. API key en .env, 3. API key en variables de entorno
        if api_key:
            client = OpenAI(api_key=api_key)
        else:
            # .env ya está cargado por dotenv
            api_key_env = os.environ.get("OPENAI_API_KEY")
            if api_key_env:
                client = OpenAI(api_key=api_key_env)
        
        return client is not None, "Cliente OpenAI inicializado correctamente" if client else "No se pudo inicializar el cliente OpenAI. Ingrese una clave API válida."
    except ImportError:
        return False, "Error: El paquete OpenAI no está instalado. Instálelo con 'pip install openai'"
    except Exception as e:
        return False, f"Error al inicializar OpenAI: {str(e)}"

def get_system_prompt_by_type(tipo, etiquetas=""):
    """Genera el prompt del sistema según el tipo de contenido y etiquetas"""
    etiquetas_formatted = f" sobre {etiquetas}" if etiquetas else ""
    
    prompts = {
        "Historia": f"Eres un creador de historias realistas{etiquetas_formatted}. Crea historias directamente sin dar títulos ni introducciones, solo el texto de la historia. Sé descriptivo y emotivo.",
        
        "Resumen": f"Eres un redactor que realiza resúmenes concisos{etiquetas_formatted}. Proporciona resúmenes directos y al grano, sin introductores ni conclusiones, solo el contenido principal.",
        
        "Cuento": f"Eres un narrador de cuentos{etiquetas_formatted}. Crea cuentos directamente sin dar títulos ni aclaraciones, solo la narrativa. Usa un lenguaje colorido y atractivo.",
        
        "Fantasía": f"Eres un creador de historias de fantasía{etiquetas_formatted}. Crea mundos imaginarios con elementos mágicos. No añadas títulos ni aclaraciones, solo el texto de la historia.",
        
        "Chisme": f"Eres un narrador de chismes y rumores{etiquetas_formatted}. Cuenta historias jugosas y controversiales pero plausibles. No añadas introducciones ni conclusiones, solo el chisme en sí.",
        
        "Curiosidades": f"Eres un experto en curiosidades{etiquetas_formatted}. Proporciona datos interesantes y poco conocidos directamente, sin introducción ni preámbulos.",
        
        "Datos": f"Eres un experto que proporciona datos concretos{etiquetas_formatted}. Entrega información precisa y concisa sin introducciones ni conclusiones, solo los datos relevantes."
    }
    
    # Si el tipo no está en el diccionario, usar Historia como default
    return prompts.get(tipo, prompts["Historia"])

def get_user_prompt_by_type(tipo, texto_prompt):
    """Genera el prompt del usuario según el tipo de contenido"""
    prompts = {
        "Historia": f"Crea una historia completa sin título, sin introducción, y sin conclusión del tipo 'fin'. Simplemente escribe la historia como tal, debe tener aproximadamente 4 párrafos, sobre: {texto_prompt}",
        
        "Resumen": f"Haz un resumen completo sin título, sin viñetas, sin puntos numerados, y sin conclusión. Solo el texto directo resumiendo lo siguiente: {texto_prompt}",
        
        "Cuento": f"Narra un cuento completo sin título, sin moraleja explícita al final, y sin fórmulas como 'érase una vez' o 'colorín colorado'. Solo el texto del cuento sobre: {texto_prompt}",
        
        "Fantasía": f"Crea una historia de fantasía sin título, sin prólogo ni epílogo. Solo la narrativa directa sobre: {texto_prompt}",
        
        "Chisme": f"Cuenta un chisme o rumor jugoso sin introducción tipo 'te cuento que' ni conclusión. Solo la información directa sobre: {texto_prompt}",
        
        "Curiosidades": f"Proporciona 3-4 curiosidades interesantes sin títulos, sin numeración, y sin frases como 'sabías que'. Solo la información directa sobre: {texto_prompt}",
        
        "Datos": f"Proporciona datos concretos sin introducción, sin enumerarlos, y sin conclusión. Solo la información directa sobre: {texto_prompt}"
    }
    
    return prompts.get(tipo, prompts["Historia"])

def generar_texto_con_openai(prompt, tipo="Historia", etiquetas="", api_key=None):
    """Genera texto usando OpenAI API según el tipo de contenido y etiquetas"""
    global client
    
    # Si se proporcionó una API key, intentar inicializar el cliente
    if api_key and not client:
        success, _ = inicializar_openai_client(api_key)
        if not success:
            return "Error: No se pudo inicializar el cliente OpenAI con la clave proporcionada."
    
    if not client:
        return "Error: Cliente OpenAI no inicializado. Por favor ingrese una clave API válida en la pestaña de configuración."
    
    try:
        # Obtener los prompts específicos para el tipo de contenido
        system_prompt = get_system_prompt_by_type(tipo, etiquetas)
        user_prompt = get_user_prompt_by_type(tipo, prompt)
        
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            seed=abs(hash(prompt)) % 10000000,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        return f"Error al generar texto con OpenAI: {str(e)}"

# Intentar inicializar OpenAI al inicio usando la clave en .env
inicializar_openai_client()