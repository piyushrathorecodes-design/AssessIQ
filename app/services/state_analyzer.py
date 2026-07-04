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
    Analyzes the FULL message history to reconstruct the recruiter's hiring criteria.
    Merges with previous_state using null-safe logic so no field is lost.
    """
    if not messages:
        return previous_state or ConversationState()

    # Format the complete message history
    formatted_history = []
    for m in messages:
        role_label = "Recruiter" if m.role == "user" else "Assistant"
        formatted_history.append(f"{role_label}: {m.content}")
    history_text = "\n".join(formatted_history)

    # Format previous state for prompt injection
    prev_state_json = "{}"
    if previous_state:
        prev_state_json = json.dumps(previous_state.model_dump(), indent=2)

    try:
        analyzer_template = load_prompt("state_analyzer_prompt.txt")
        prompt = analyzer_template.replace("{history}", history_text).replace("{previous_state}", prev_state_json)

        response_text = llm_service.call_llm(prompt, json_mode=True, temperature=0.0)
        state_dict = json.loads(response_text)

        # --- Null-safe merge: never overwrite a known value with null ---
        # If LLM returns null for a field but we already had a value, keep the old value.
        prev = previous_state.model_dump() if previous_state else {}

        def coalesce(new_val, old_val):
            """Return new_val if it is non-null/non-empty, else old_val."""
            if isinstance(new_val, list):
                return new_val if new_val else old_val
            return new_val if new_val is not None else old_val

        state = ConversationState(
            job_role=coalesce(state_dict.get("job_role"), prev.get("job_role")),
            experience_level=coalesce(state_dict.get("experience_level"), prev.get("experience_level")),
            required_skills=coalesce(state_dict.get("required_skills", []), prev.get("required_skills", [])),
            test_types=coalesce(state_dict.get("test_types", []), prev.get("test_types", [])),
            remote_testing=coalesce(state_dict.get("remote_testing"), prev.get("remote_testing")),
            adaptive=coalesce(state_dict.get("adaptive"), prev.get("adaptive")),
        )

        logger.info(f"Reconstructed Conversation State: {state.model_dump()}")
        return state

    except Exception as e:
        logger.error(f"Error during conversation state analysis: {e}")
        # Return previous known state rather than blank state on failure
        return previous_state or ConversationState()


def check_clarification_need(
    messages: List[Message],
    state: ConversationState
) -> Tuple[bool, str]:
    """
    Evaluates if we need to ask clarifying questions based on the extracted state.
    Returns: (needs_clarification, clarification_question)

    IMPORTANT: Only ask for clarification if the information is truly missing.
    If job_role OR required_skills is already known, proceed to retrieval.
    """
    # If we have a job role OR specific skills, that is enough to retrieve.
    # Do NOT ask for more information - proceed to recommendations.
    if state.job_role or state.required_skills:
        logger.info("Sufficient criteria found. Skipping clarification.")
        return False, ""

    # Both job_role and required_skills are missing. Ask for the role.
    # First attempt an LLM-powered clarification decision for nuance.
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

        system_instructions = clarification_template
        response_text = llm_service.call_llm(prompt, system_instruction=system_instructions, json_mode=True, temperature=0.0)
        result = json.loads(response_text)

        needs_clarify = bool(result.get("needs_clarification", False))
        question = result.get("clarification_question", "").strip()

        if needs_clarify and not question:
            question = "Could you specify what job role or department you are hiring for? (e.g., Software Engineer, Sales Manager)"

        logger.info(f"Clarification assessment: needs_clarify={needs_clarify}")
        return needs_clarify, question

    except Exception as e:
        logger.error(f"Error checking clarification need: {e}")
        # Fallback: ask for role since we know it is missing
        return True, "Could you specify what job role or department you are hiring for? (e.g., Software Engineer, Sales Manager)"


