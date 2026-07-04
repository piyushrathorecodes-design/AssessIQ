import json
import logging
from typing import List, Optional, Tuple
import app.services.llm_service as llm_service
from app.prompts.loader import load_prompt
from app.models.domain import Message, ConversationState

logger = logging.getLogger("shl_recommender")

def analyze_conversation_state(
    messages: List[Message],
    previous_state: Optional[ConversationState] = None
) -> ConversationState:
    """
    Analyzes message history to reconstruct the recruiter's hiring criteria.
    Updates any prior state dynamically if the recruiter refines their constraints.
    """
    if not messages:
        return ConversationState()
        
    # Format message history
    formatted_history = []
    for m in messages:
        role_label = "Recruiter" if m.role == "user" else "Assistant"
        formatted_history.append(f"{role_label}: {m.content}")
    history_text = "\n".join(formatted_history)
    
    # Format previous state
    prev_state_json = "{}"
    if previous_state:
        prev_state_json = json.dumps(previous_state.model_dump(), indent=2)
        
    try:
        analyzer_template = load_prompt("state_analyzer_prompt.txt")
        prompt = analyzer_template.replace("{history}", history_text).replace("{previous_state}", prev_state_json)
        
        response_text = llm_service.call_llm(prompt, json_mode=True, temperature=0.0)
        state_dict = json.loads(response_text)
        
        # Instantiate updated state
        state = ConversationState(
            job_role=state_dict.get("job_role"),
            experience_level=state_dict.get("experience_level"),
            required_skills=state_dict.get("required_skills", []),
            test_types=state_dict.get("test_types", []),
            remote_testing=state_dict.get("remote_testing"),
            adaptive=state_dict.get("adaptive")
        )
        
        logger.info(f"Reconstructed Conversation State: {state.model_dump()}")
        return state
        
    except Exception as e:
        logger.error(f"Error during conversation state analysis: {e}")
        # Return fallback state
        return previous_state or ConversationState()

def check_clarification_need(
    messages: List[Message],
    state: ConversationState
) -> Tuple[bool, str]:
    """
    Evaluates if we need to ask clarifying questions based on the extracted state.
    Returns: (needs_clarification, clarification_question)
    """
    # Quick logical heuristics to bypass LLM call for empty inputs
    if not state.job_role and not state.required_skills:
        return True, "Could you specify what job role or department you are hiring for? (e.g., Software Engineer, Sales Manager)"
        
    # Format history for LLM double check
    formatted_history = []
    for m in messages:
        role_label = "Recruiter" if m.role == "user" else "Assistant"
        formatted_history.append(f"{role_label}: {m.content}")
    history_text = "\n".join(formatted_history)
    
    try:
        clarification_template = load_prompt("clarification_prompt.txt")
        prompt = f"""
        Based on the current extracted criteria:
        {json.dumps(state.model_dump(), indent=2)}
        
        And the conversation history:
        {history_text}
        
        Determine if we need clarifying details. Output JSON.
        """
        
        # Load the base clarification instruction/prompt and merge
        system_instructions = clarification_template
        
        response_text = llm_service.call_llm(prompt, system_instruction=system_instructions, json_mode=True, temperature=0.0)
        result = json.loads(response_text)
        
        needs_clarify = bool(result.get("needs_clarification", False))
        question = result.get("clarification_question", "").strip()
        
        if needs_clarify and not question:
            # Fallback question
            question = "Could you please tell me a bit more about the skills or seniority level you require?"
            
        logger.info(f"Clarification assessment: needs_clarify={needs_clarify}")
        return needs_clarify, question
        
    except Exception as e:
        logger.error(f"Error checking clarification need: {e}")
        # Default fallback
        if not state.job_role:
            return True, "Could you tell me the job role or title you are recruiting for?"
        return False, ""

