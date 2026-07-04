import json
import logging
from typing import List, Dict, Any, Tuple, Optional
import re

from app.config.settings import settings
from app.models.domain import Message, ConversationState, Assessment
import app.services.llm_service as llm_service
from app.services.classifier import classify_intent
from app.services.state_analyzer import analyze_conversation_state, check_clarification_need
from app.rag.retriever import HybridRetriever
from app.prompts.loader import load_prompt

logger = logging.getLogger("shl_recommender")

# Initialize global retriever lazily
_retriever: Optional[HybridRetriever] = None

def get_retriever() -> HybridRetriever:
    global _retriever
    if _retriever is None:
        _retriever = HybridRetriever()
    return _retriever

def format_assessments_for_context(assessments: List[Assessment]) -> str:
    """Format retrieved assessments as a text block for prompt injection."""
    parts = []
    for idx, a in enumerate(assessments):
        parts.append(
            f"[{idx + 1}] Name: {a.name}\n"
            f"URL: {a.url}\n"
            f"Category: {a.category}\n"
            f"Description: {a.description}\n"
            f"Skills: {', '.join(a.skills)}\n"
            f"Test Type Code(s): {', '.join(a.test_type)}\n"
            f"Duration: {a.duration if a.duration else 'Not specified'} mins\n"
            f"Remote Testing Support: {'Yes' if a.remote_testing_support else 'No'}\n"
            f"Adaptive: {'Yes' if a.adaptive else 'No'}\n"
            f"----------------------------------------"
        )
    return "\n".join(parts)

def handle_chat(messages: List[Message]) -> Dict[str, Any]:
    """
    Main entry point for stateless conversation orchestration.
    Coordinates intent classification, criteria state extraction, 
    guardrails, hybrid retrieval, and grounded RAG answer generation.
    """
    if not messages:
        return {
            "reply": "Welcome to the SHL Assessment Recommendation portal. I can help you discover the correct assessments from the catalog. What job role are you recruiting for?",
            "recommendations": [],
            "end_of_conversation": False
        }
        
    latest_message_obj = messages[-1]
    latest_query = latest_message_obj.content.strip()
    
    # 1. Intent Classification
    intent, confidence = classify_intent(messages)
    
    # 2. Guardrails & Refusals (Prompt Injection / Off-Topic)
    if intent in ("prompt_injection", "off_topic"):
        refusal_template = load_prompt("refusal_prompt.txt")
        prompt = refusal_template.replace("{user_query}", latest_query)
        
        response_text = llm_service.call_llm(prompt, json_mode=True, temperature=0.0)
        try:
            result = json.loads(response_text)
            return {
                "reply": result.get("reply", "I can only help you find or compare assessments from the SHL catalog. Let's get back on topic. What role are you hiring for?"),
                "recommendations": [],
                "end_of_conversation": False
            }
        except Exception:
            return {
                "reply": "I apologize, but I can only answer questions related to the SHL Assessment Solutions catalog. How can I help you select the right test for your candidates?",
                "recommendations": [],
                "end_of_conversation": False
            }
            
    # 3. Greeting
    if intent == "greeting":
        system_prompt = load_prompt("system_prompt.txt")
        prompt = f"""
        Recruiter said: "{latest_query}"
        Provide a friendly, professional greeting. Briefly introduce your capability to recommend and compare assessments from the SHL Individual Test Solutions catalog, and ask what job role they need assessments for.
        """
        response_text = llm_service.call_llm(prompt, system_instruction=system_prompt, json_mode=True, temperature=0.2)
        try:
            result = json.loads(response_text)
            return {
                "reply": result.get("reply", "Hello! I am your SHL Assessment advisor. Tell me about the job role or skills you are seeking to evaluate, and I will recommend matching tests."),
                "recommendations": [],
                "end_of_conversation": False
            }
        except Exception:
            return {
                "reply": "Hello! I am your SHL Assessment advisor. I can help you find and compare tests. What job role are you recruiting for?",
                "recommendations": [],
                "end_of_conversation": False
            }

    # 4. Goodbye
    if intent == "goodbye":
        prompt = f"""
        Recruiter said: "{latest_query}"
        Formulate a brief, polite closing goodbye.
        """
        response_text = llm_service.call_llm(prompt, json_mode=True, temperature=0.2)
        try:
            result = json.loads(response_text)
            return {
                "reply": result.get("reply", "Thank you for visiting. Good luck with your hiring!"),
                "recommendations": [],
                "end_of_conversation": True
            }
        except Exception:
            return {
                "reply": "Thank you for using the SHL Assessment portal. Goodbye!",
                "recommendations": [],
                "end_of_conversation": True
            }

    # 5. Process Recommendation, Refinement, or Comparison Request
    # Reconstruct state from full history
    state = analyze_conversation_state(messages)
    
    # 6. Check if we need Clarification first
    # Exception: if user is asking to compare specific tests, we don't block on clarification
    is_explicit_comparison = (intent == "comparison_request" and 
                              any(acronym in latest_query.upper() for acronym in ["OPQ", "GSA", "SJT", "VERIFY", "CHECKING"]))
    
    if not is_explicit_comparison:
        needs_clarify, clarify_question = check_clarification_need(messages, state)
        if needs_clarify:
            logger.info("Recruiter profile is incomplete. Asking clarifying question.")
            return {
                "reply": clarify_question,
                "recommendations": [],
                "end_of_conversation": False
            }

    # 7. Execute Search
    retriever = get_retriever()
    
    if intent == "comparison_request":
        # Extract comparison candidates from the user query
        # We perform exact and fuzzy matching against catalog names
        compared_assessments: List[Assessment] = []
        
        # Look for tokens in query that match our catalog entries
        for a in retriever.assessments:
            # Match short acronyms (e.g. OPQ32, OPQ, GSA, SJT)
            acronym_match = False
            acronyms = ["OPQ", "OPQ32", "GSA", "SJT"]
            for ac in acronyms:
                if ac in latest_query.upper() and ac in a.name.upper():
                    acronym_match = True
            
            # Match substring names
            name_words = [w.lower() for w in a.name.split() if len(w) > 3]
            fuzzy_match = any(w in latest_query.lower() for w in name_words) if name_words else False
            
            if acronym_match or fuzzy_match:
                if a not in compared_assessments:
                    compared_assessments.append(a)
                    
        # If we found matches to compare (at least 2 is preferred, but 1 is fine if comparing against others)
        if not compared_assessments or len(compared_assessments) < 2:
            # Retrieve top matches for comparison
            retrieved = retriever.retrieve(latest_query, state, top_k=3)
            # Merge with any found
            for r in retrieved:
                if r not in compared_assessments:
                    compared_assessments.append(r)
                    
        # Limit to top 3 for comparison comparison display
        compared_assessments = compared_assessments[:3]
        
        logger.info(f"Comparing assessments: {[a.name for a in compared_assessments]}")
        context_text = format_assessments_for_context(compared_assessments)
        
        comp_template = load_prompt("comparison_prompt.txt")
        prompt = comp_template.replace("{assessments_to_compare}", ", ".join([a.name for a in compared_assessments])).replace("{retrieved_documents}", context_text)
        
        system_prompt = load_prompt("system_prompt.txt")
        response_text = llm_service.call_llm(prompt, system_instruction=system_prompt, json_mode=True, temperature=0.0)
        
        try:
            result = json.loads(response_text)
            return {
                "reply": result.get("reply", "Comparison complete."),
                "recommendations": [],
                "end_of_conversation": False
            }
        except Exception as e:
            logger.error(f"Error parsing comparison result: {e}")
            return {
                "reply": "I apologize, I encountered an issue formatting the comparison of these tests. Let me know if you would like me to list details for a single assessment instead.",
                "recommendations": [],
                "end_of_conversation": False
            }
            
    else:
        # Default: Recommendation Request or Refinement
        # Search index based on user state
        search_query = f"{state.job_role or ''} {' '.join(state.required_skills)}"
        if not search_query.strip():
            search_query = latest_query
            
        logger.info(f"Retrieving recommendations for query: '{search_query}'")
        retrieved = retriever.retrieve(search_query, state, top_k=5)
        
        context_text = format_assessments_for_context(retrieved)
        criteria_text = json.dumps(state.model_dump(), indent=2)
        
        rec_template = load_prompt("recommendation_prompt.txt")
        prompt = rec_template.replace("{criteria}", criteria_text).replace("{retrieved_documents}", context_text)
        
        system_prompt = load_prompt("system_prompt.txt")
        response_text = llm_service.call_llm(prompt, system_instruction=system_prompt, json_mode=True, temperature=0.0)
        
        try:
            result = json.loads(response_text)
            
            # Strictly validate recommendation URLs match catalog.json to prevent hallucinations
            clean_recs = []
            for rec in result.get("recommendations", []):
                rec_name = rec.get("name", "").strip()
                rec_url = rec.get("url", "").strip()
                rec_type = rec.get("test_type", "").strip()
                
                # Verify match in retrieved list to preserve exact metadata & url
                matched = False
                for r in retrieved:
                    if r.name.lower() == rec_name.lower() or r.url == rec_url:
                        # Normalize to catalog details
                        clean_recs.append({
                            "name": r.name,
                            "url": r.url,
                            "test_type": ", ".join(r.test_type) if isinstance(r.test_type, list) else r.test_type
                        })
                        matched = True
                        break
                        
                if not matched:
                    # Fallback to direct mapping from catalog if LLM hallucinated slightly
                    for r in retriever.assessments:
                        if r.name.lower() == rec_name.lower():
                            clean_recs.append({
                                "name": r.name,
                                "url": r.url,
                                "test_type": ", ".join(r.test_type) if isinstance(r.test_type, list) else r.test_type
                            })
                            matched = True
                            break
                            
            return {
                "reply": result.get("reply", "Recommendations complete."),
                "recommendations": clean_recs,
                "end_of_conversation": False
            }
            
        except Exception as e:
            logger.error(f"Error parsing recommendation result: {e}")
            return {
                "reply": "I have found some assessments that fit your needs, but I encountered an error formatting them. Please let me know if you would like me to try again.",
                "recommendations": [],
                "end_of_conversation": False
            }
