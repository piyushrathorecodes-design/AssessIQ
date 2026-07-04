import os
import json
import logging
import time
from typing import Optional, Dict, Any, List
import google.generativeai as genai
from google.generativeai.types import GenerationConfig

from app.config.settings import settings

logger = logging.getLogger("shl_recommender")

# Configure basic logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler()]
)

# Initialize Gemini API key
api_key = settings.google_api_key
if not api_key:
    # Try fallback to GEMINI_API_KEY
    api_key = os.getenv("GEMINI_API_KEY", "")
    
if api_key:
    genai.configure(api_key=api_key)
    logger.info("Gemini API key configured successfully.")
else:
    logger.warning("Gemini API key not found in environment (GOOGLE_API_KEY or GEMINI_API_KEY). Ensure key is set before running RAG operations.")

def call_llm(
    prompt: str,
    system_instruction: Optional[str] = None,
    json_mode: bool = True,
    temperature: float = 0.0,
    retries: int = 3
) -> str:
    """
    Invokes the Google Gemini API with error handling, logging, and retry logic.
    """
    if not api_key:
        logger.error("Attempted to call LLM but Gemini API Key is missing.")
        raise ValueError("Gemini API key is not configured. Please check settings.")

    # Configure generation parameters
    gen_config = {
        "temperature": temperature,
        "max_output_tokens": 2048,
    }
    if json_mode:
        gen_config["response_mime_type"] = "application/json"

    # Use the model from settings (e.g. gemini-1.5-flash or gemini-2.5-flash)
    model_name = settings.model_name
    # Fallback/Map default names if needed
    if "gemini-" not in model_name:
        model_name = "gemini-1.5-flash"
        
    logger.info(f"Invoking LLM Model={model_name} (JSON={json_mode})")
    start_time = time.time()
    
    for attempt in range(retries):
        try:
            model = genai.GenerativeModel(
                model_name=model_name,
                generation_config=GenerationConfig(**gen_config),
                system_instruction=system_instruction
            )
            
            response = model.generate_content(prompt)
            latency = time.time() - start_time
            logger.info(f"LLM Response succeeded in {latency:.3f} seconds.")
            
            # Log first few characters of the response
            text_out = response.text.strip()
            logger.debug(f"LLM Output: {text_out[:100]}...")
            return text_out
            
        except Exception as e:
            latency = time.time() - start_time
            logger.warning(f"LLM call failed on attempt {attempt + 1} (latency: {latency:.3f}s): {e}")
            if attempt < retries - 1:
                # Exponential backoff
                time.sleep((2 ** attempt) + 0.5)
            else:
                logger.error("Max LLM retries reached.")
                raise e
                
    return "{}"
