import json
import logging
from typing import List, Dict, Any, Tuple
import app.services.llm_service as llm_service
from app.prompts.loader import load_prompt
from app.models.domain import Message

logger = logging.getLogger("shl_recommender")

def format_history_as_text(messages: List[Message]) -> str:
    """Format message list as string history for LLM prompt."""
    if not messages:
        return "[No prior messages]"
    formatted = []
    for m in messages[:-1]:  # exclude the latest one
        role_label = "Recruiter" if m.role == "user" else "Assistant"
        formatted.append(f"{role_label}: {m.content}")
    return "\n".join(formatted) if formatted else "[No prior messages]"

def classify_intent(messages: List[Message]) -> Tuple[str, float]:
    """
    Classifies the recruiter's query into Greeting, Goodbye, Recommendation,
    Refinement, Comparison, Prompt Injection, or Off-Topic.
    """
    if not messages:
        return "greeting", 1.0
        
    latest_message = messages[-1].content
    history_text = format_history_as_text(messages)
    
    try:
        classifier_template = load_prompt("classifier_prompt.txt")
        prompt = classifier_template.replace("{history}", history_text).replace("{latest_message}", latest_message)
        
        response_text = llm_service.call_llm(prompt, json_mode=True, temperature=0.0)
        result = json.loads(response_text)
        
        intent = result.get("intent", "recommendation_request").strip().lower()
        confidence = float(result.get("confidence", 0.8))
        
        logger.info(f"Intent classified: {intent} (confidence: {confidence:.2f})")
        return intent, confidence
        
    except Exception as e:
        logger.error(f"Error during intent classification: {e}")
        # Default fallback to recommendation
        return "recommendation_request", 0.5
