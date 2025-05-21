import torch
from transformers import AutoTokenizer, AutoModelForSeq2SeqLM, pipeline
from tqdm import tqdm
import gc

class TranslationManager:
    def __init__(self):
        self.translator = None
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        print(f"Usando dispositivo: {self.device}")

    def load_model(self, source_lang, target_lang):
        """Carga el modelo de traducción usando pipeline"""
        if self.translator is None:
            try:
                model_name = "facebook/nllb-200-distilled-600M"
                print(f"Cargando modelo {model_name}...")
                
                # Crear el pipeline de traducción
                self.translator = pipeline(
                    'translation',
                    model=model_name,
                    device=0 if self.device == "cuda" else -1,
                    src_lang=self.get_nllb_code(source_lang),
                    tgt_lang=self.get_nllb_code(target_lang)
                )
                
                print("Pipeline de traducción cargado exitosamente")
            except Exception as e:
                print(f"Error al cargar el pipeline: {str(e)}")
                raise

    def get_nllb_code(self, lang_code):
        """Convierte códigos ISO a códigos NLLB"""
        lang_map = {
            'es': 'spa_Latn',
            'en': 'eng_Latn',
            'fr': 'fra_Latn',
            'de': 'deu_Latn',
            'it': 'ita_Latn',
            'pt': 'por_Latn',
        }
        return lang_map.get(lang_code, 'eng_Latn')

    def translate_single(self, text):
        """Traduce un solo texto usando el pipeline"""
        if not text or len(text.strip()) == 0:
            return ""
            
        try:
            # Traducir usando el pipeline
            result = self.translator(
                text.strip(),
                max_length=256,
                num_beams=5,
                length_penalty=1.0,
                early_stopping=True
            )
            
            # Extraer la traducción
            translation = result[0]['translation_text'].strip()
            return translation if translation else text
            
        except Exception as e:
            print(f"Error en traducción: {str(e)}")
            return text

    def translate_segments(self, segments, source_lang, target_lang):
        """Traduce los segmentos usando el pipeline"""
        # Cargar el modelo con los idiomas correctos
        self.load_model(source_lang, target_lang)
        translated_segments = []
        
        print(f"Iniciando traducción de {len(segments)} segmentos...")
        
        for i, segment in enumerate(tqdm(segments, desc="Traduciendo")):
            try:
                original_text = segment['text'].strip()
                
                if not original_text:
                    translated_text = original_text
                else:
                    translated_text = self.translate_single(original_text)

                translated_segments.append({
                    'start': segment['start'],
                    'end': segment['end'],
                    'text': translated_text if translated_text else original_text
                })

            except Exception as e:
                print(f"Error en segmento {i+1}: {str(e)}")
                translated_segments.append(segment)
                if self.device == "cuda":
                    torch.cuda.empty_cache()

        return translated_segments

    def __del__(self):
        """Limpieza al destruir la instancia"""
        if self.device == "cuda":
            torch.cuda.empty_cache()
        gc.collect()