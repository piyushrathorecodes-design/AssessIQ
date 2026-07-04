import logging
from fastapi import APIRouter, HTTPException

from app.models.schemas import ChatRequest, ChatResponse, APIRecommendation
from app.models.domain import Message
from app.services.chat_orchestrator import handle_chat

logger = logging.getLogger("shl_recommender")
router = APIRouter()

@router.get("/health")
def health_check():
    """Health endpoint returning ok status."""
    return {"status": "ok"}

@router.post("/chat", response_model=ChatResponse)
def chat_interaction(request: ChatRequest):
    """
    Stateless conversational recommender route.
    Receives message history, runs RAG matching, and returns grounding response.
    """
    logger.info(f"Received /chat request with {len(request.messages)} messages.")
    
    if not request.messages:
        raise HTTPException(status_code=400, detail="Message list cannot be empty.")
        
    try:
        # Translate API schemas to domain objects
        domain_messages = [
            Message(role=m.role, content=m.content) 
            for m in request.messages
        ]
        
        # Run orchestrator
        orchestration_result = handle_chat(domain_messages)
        
        # Map output to API schemas
        recs = [
            APIRecommendation(
                name=r["name"],
                url=r["url"],
                test_type=r["test_type"]
            )
            for r in orchestration_result.get("recommendations", [])
        ]
        
        response = ChatResponse(
            reply=orchestration_result["reply"],
            recommendations=recs,
            end_of_conversation=bool(orchestration_result.get("end_of_conversation", False))
        )
        
        logger.info(f"Returning /chat response. End of conversation: {response.end_of_conversation}")
        return response
        
    except Exception as e:
        logger.error(f"Error in /chat route: {e}", exc_info=True)
        raise HTTPException(
            status_code=500, 
            detail=f"Error executing conversation engine: {str(e)}"
        )
