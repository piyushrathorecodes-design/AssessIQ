import os
import sys
import pytest
from fastapi.testclient import TestClient

# Add project root to python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.main import app
from app.rag.retriever import HybridRetriever

@pytest.fixture
def client():
    """Provides a TestClient for checking FastAPI routes."""
    return TestClient(app)

@pytest.fixture
def mock_llm_response(monkeypatch):
    """Fixture to patch LLM calls and return predictable JSON responses based on prompt keywords."""
    import app.services.llm_service
    
    def fake_call_llm(prompt, system_instruction=None, json_mode=True, temperature=0.0, retries=3):
        prompt_upper = prompt.upper()
        
        # 1. Intent Classifier Mocking
        if "VALID INTENTS" in prompt_upper or "INTENT CLASSIFIER" in prompt_upper:
            latest_msg = ""
            if "LATEST USER MESSAGE:" in prompt_upper:
                latest_msg_section = prompt_upper.split("LATEST USER MESSAGE:")[-1]
                latest_msg = latest_msg_section.split("### TASK:")[0].strip()
            
            if "HELLO" in latest_msg or "HI!" in latest_msg:
                return '{"intent": "greeting", "confidence": 0.99}'
            elif "BYE" in latest_msg or "EXIT" in latest_msg:
                return '{"intent": "goodbye", "confidence": 0.99}'
            elif "COMPARE" in latest_msg or "VS" in latest_msg:
                return '{"intent": "comparison_request", "confidence": 0.95}'
            elif "ACTUALLY" in latest_msg:
                return '{"intent": "refinement", "confidence": 0.90}'
            elif "IGNORE" in latest_msg or "JAILBREAK" in latest_msg:
                return '{"intent": "prompt_injection", "confidence": 0.99}'
            elif "FRANCE" in latest_msg or "PRESIDENT" in latest_msg or "POLITICS" in latest_msg:
                return '{"intent": "off_topic", "confidence": 0.99}'
            else:
                return '{"intent": "recommendation_request", "confidence": 0.90}'

        # 2. Clarification Check Mocking (must come BEFORE state analyzer because the
        #    clarification prompt also contains "CONVERSATION HISTORY" which would
        #    otherwise be caught by the state analyzer branch below)
        elif "CLARIFYING DETAILS" in prompt_upper or "CLARIFICATION_PROMPT" in prompt_upper:
            history_part = ""
            if "RECRUITER:" in prompt_upper:
                history_part = prompt_upper

            if "JAVA DEVELOPER" in history_part:
                return '{"needs_clarification": false, "missing_details": [], "clarification_question": ""}'
            else:
                return '{"needs_clarification": true, "missing_details": ["job_role"], "clarification_question": "What job role or skills do you want to evaluate?"}'

        # 3. State Analyzer Mocking
        elif "EXTRACT AND UPDATE" in prompt_upper or "CONVERSATION HISTORY" in prompt_upper:
            history_part = ""
            if "CONVERSATION HISTORY:" in prompt_upper:
                history_part = prompt_upper.split("CONVERSATION HISTORY:")[-1].split("PREVIOUS STATE")[0]

            if "JAVA DEVELOPER" in history_part:
                return '{"job_role": "Java Developer", "experience_level": null, "required_skills": ["Java", "OOP"], "test_types": ["K"], "remote_testing": null, "adaptive": null}'
            elif "ACTUALLY INCLUDE PERSONALITY" in history_part or "PERSONALITY" in history_part:
                return '{"job_role": "Java Developer", "experience_level": null, "required_skills": ["Java"], "test_types": ["K", "P"], "remote_testing": null, "adaptive": null}'
            else:
                return '{"job_role": null, "experience_level": null, "required_skills": [], "test_types": [], "remote_testing": null, "adaptive": null}'

        # 4. Comparison Request Mocking
        elif "ASSESSMENTS TO COMPARE" in prompt_upper:
            return '{"reply": "Here is a comparison of OPQ32 and Verify Interactive G+ in a table format:\\n| Feature | OPQ32 | Verify G+ |\\n|---|---|---|\\n| Type | Personality | Cognitive |\\n| Duration | 45 min | 36 min |", "recommendations": []}'

        # 5. Guardrails / Refusal Mocking
        elif "REFUSAL" in prompt_upper or "OUT OF SCOPE" in prompt_upper or "SUBMITTED A QUERY" in prompt_upper:
            return '{"reply": "I apologize, but my only function is to recommend and compare SHL assessments from the catalog. I cannot answer queries on other topics.", "recommendations": []}'

        # 6. Recommendation Mocking (Fallback default)
        else:
            return '''{
                "reply": "I recommend the following tests for your Java Developer role: Java Software Engineer Simulation and Verify Interactive G+.",
                "recommendations": [
                    {
                        "name": "Java Software Engineer Simulation",
                        "url": "https://www.shl.com/solutions/products/product-catalog/view/java-software-engineer-simulation/",
                        "test_type": "S, K"
                    },
                    {
                        "name": "Verify Interactive G+ (General Ability)",
                        "url": "https://www.shl.com/solutions/products/product-catalog/view/verify-interactive-g-plus-general-ability/",
                        "test_type": "A"
                    }
                ]
            }'''

    monkeypatch.setattr(app.services.llm_service, "call_llm", fake_call_llm)
