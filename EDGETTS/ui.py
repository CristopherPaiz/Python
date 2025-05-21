# -*- coding: utf-8 -*-
import gradio as gr
from tts_engine import sintetizar_voz
from openai_client import inicializar_openai_client
from data_manager import (
    inicializar_tabla, cargar_json, guardar_json, 
    crear_archivo_json, on_table_change, agregar_fila,
    guardar_json_auto, TIPOS_CONTENIDO
)
from audio_processor import generar_audio_desde_json

def actualizar_voces_por_filtro(mostrar_solo_espanol, voces_edge_tts, voces_espanol):
    """Actualiza el selector de voces según el filtro seleccionado"""
    if mostrar_solo_espanol:
        opciones_espanol = [(voz[1], voz[2]) for voz in voces_espanol]  # (texto_numerado, nombre_corto)
        voz_default = next((voz[2] for voz in voces_espanol if voz[2] == "es-BO-MarceloNeural"), opciones_espanol[0][1] if opciones_espanol else None)
        return gr.update(choices=opciones_espanol, value=voz_default)
    else:
        opciones_todas = [(voz.split(" - ")[0], voz.split(" - ")[0]) for voz in voces_edge_tts]
        voz_default = "es-BO-MarceloNeural"
        return gr.update(choices=opciones_todas, value=voz_default)

def crear_interfaz(voces_edge_tts, voces_espanol):
    """Crea la interfaz de Gradio"""
    opciones_espanol = [(voz[1], voz[2]) for voz in voces_espanol]  # (texto_numerado, nombre_corto)
    
    voz_default = next((voz[2] for voz in voces_espanol if voz[2] == "es-BO-MarceloNeural"), 
                      opciones_espanol[0][1] if opciones_espanol else None)
    
    with gr.Blocks(title="Sintetizador de Voz Edge TTS con JSON", theme=gr.themes.Soft()) as interfaz:
        gr.Markdown("""
        # 🎤 Sintetizador de Voz con Edge TTS y JSON
        """)
        
        with gr.Tab("Editor JSON"):
            gr.Markdown("### Edita los datos para generar audio")
            
            # DataFrame completamente editable
            tabla = gr.Dataframe(
                value=inicializar_tabla,
                datatype={
                    "series": "str",
                    "seed": "str",
                    "part": "str",
                    "IA": "bool",
                    "outro": "str",
                    "text": "str",
                    "textAI": "str",
                    "randomVideo": "bool",
                    "video": "str",
                    "tipo": gr.Dropdown(choices=TIPOS_CONTENIDO),
                    "etiquetas": "str"
                },
                col_count=11, 
                interactive=True,
                column_widths=[10, 10, 10, 10, 10, 10, 10, 10, 10, 10, 10],
                label="Datos para Generación de Audio",
                elem_id="tabla_datos"
            )
            
            estado_tabla = gr.Textbox(label="Estado", interactive=False)
            
            with gr.Row():
                agregar_fila_btn = gr.Button("Agregar Fila", variant="primary")
                cargar_boton = gr.UploadButton("Cargar JSON", file_types=[".json"])
                guardar_boton = gr.Button("Guardar JSON", variant="secondary")
                descargar_boton = gr.Button("Descargar JSON", variant="secondary")
            
            salida_json = gr.JSON(label="JSON Resultante", visible=False)
            texto_json = gr.Textbox(label="JSON como texto", visible=False)
            json_para_descargar = gr.File(label="Descargar JSON", visible=False)
        
        with gr.Tab("Generar Audio"):
            with gr.Row():
                with gr.Column():
                    indice_entrada = gr.Textbox(label="Número de fila a procesar (1-n)", value="1")
                    
                    filtro_espanol = gr.Checkbox(
                        label="Mostrar solo voces en español",
                        value=True,
                        info="Activa para ver solo voces en español, desactiva para ver todas las voces disponibles"
                    )
                    
                    selector_voz_edge = gr.Dropdown(
                        choices=opciones_espanol,
                        label="Seleccionar voz",
                        value=voz_default,
                        info="Selecciona la voz que deseas utilizar para la síntesis"
                    )
                    
                    selector_velocidad = gr.Slider(
                        minimum=0.5, 
                        maximum=2.0, 
                        value=1.1, 
                        step=0.05,
                        label="Velocidad de habla",
                        info="1.0 = normal, menor = más lento, mayor = más rápido"
                    )
                    
                    # Campo opcional para API Key de OpenAI
                    api_key_input = gr.Textbox(
                        label="API Key de OpenAI (opcional)", 
                        placeholder="Deja en blanco para usar la API Key global", 
                        type="password"
                    )
                    
                    boton_generar = gr.Button("Generar Audio", variant="primary")
                    mensaje_estado = gr.Textbox(label="Estado", interactive=False)
                
                with gr.Column():
                    # Salida de audio
                    audio_salida = gr.Audio(label="Audio generado")
        
        # Manejar cambios en la tabla
        tabla.change(
            fn=on_table_change,
            inputs=[tabla],
            outputs=[tabla, estado_tabla]
        )
        
        # Agregar fila
        agregar_fila_btn.click(
            fn=agregar_fila,
            inputs=[tabla],
            outputs=[tabla, estado_tabla]
        )
        
        # Manejo de eventos para la tabla y JSON
        cargar_boton.upload(
            fn=cargar_json,
            inputs=[cargar_boton],
            outputs=[tabla, estado_tabla]
        )
        
        # Guardar JSON (sobrescribe audio.json)
        guardar_boton.click(
            fn=guardar_json_auto,
            inputs=[tabla],
            outputs=[estado_tabla]
        )
        
        # Preparar JSON para descargar
        descargar_boton.click(
            fn=guardar_json,
            inputs=[tabla],
            outputs=[salida_json, texto_json]
        ).then(
            fn=crear_archivo_json,
            inputs=[texto_json],
            outputs=[json_para_descargar]
        ).then(
            fn=lambda: gr.update(visible=True),
            outputs=[json_para_descargar]
        )
        
        # Actualizar voces según filtro
        filtro_espanol.change(
            fn=actualizar_voces_por_filtro,
            inputs=[filtro_espanol, gr.State(voces_edge_tts), gr.State(voces_espanol)],
            outputs=[selector_voz_edge]
        )
        
        # Generar audio desde JSON
        boton_generar.click(
            fn=generar_audio_desde_json,
            inputs=[
                indice_entrada,
                tabla,
                selector_voz_edge,
                selector_velocidad,
                api_key_input
            ],
            outputs=[audio_salida, mensaje_estado]
        )
        
    return interfaz