
import requests
from typing import Dict, Optional
import logging
import os
from dotenv import load_dotenv

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class LanguageHandler:
    def __init__(self):
        load_dotenv()
        
        self.api_key = os.getenv('SARVAM_API_KEY')
        if not self.api_key:
            raise ValueError("SARVAM_API_KEY not found in environment variables")
            
        self.api_url = "https://api.sarvam.ai/translate"
        self.supported_languages = {
            'en-IN': 'English',
            'hi-IN': 'Hindi',
            'bn-IN': 'Bengali',
            'kn-IN': 'Kannada',
            'ml-IN': 'Malayalam',
            'mr-IN': 'Marathi',
            'od-IN': 'Odia',
            'pa-IN': 'Punjabi',
            'ta-IN': 'Tamil',
            'te-IN': 'Telugu',
            'gu-IN': 'Gujarati'
        }
        self.headers = {
            "Content-Type": "application/json",
            "api-subscription-key": self.api_key
        }

    async def translate_to_english(self, text: str, source_lang: str) -> str:
    
        if source_lang == 'en-IN':
            return text

        if source_lang not in self.supported_languages:
            logger.error(f"Unsupported language code: {source_lang}")
            return text

        try:
            payload = {
                "input": text,
                "source_language_code": source_lang,
                "target_language_code": "en-IN",
                "speaker_gender": "Male",
                "mode": "formal",
                "model": "mayura:v1",
                "enable_preprocessing": True
            }

            response = requests.post(
                self.api_url,
                json=payload,
                headers=self.headers,
                timeout=30
            )
            response.raise_for_status()
            
            result = response.json()
            print(result)
            translated_text = result.get('output', text)
            
            logger.info(f"Translated text from {self.supported_languages[source_lang]} to English")
            return translated_text

        except requests.exceptions.Timeout:
            logger.error("Translation request timed out")
            return text
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Translation API error: {str(e)}")
            return text
