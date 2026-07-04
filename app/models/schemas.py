from pydantic import BaseModel, Field
from typing import List, Optional

class APIMessage(BaseModel):
    """
    API representation of a chat message in the conversation.
    """
    role: str = Field(description="Role of the message author: 'user' or 'assistant'")
    content: str = Field(description="The textual content of the message")

class ChatRequest(BaseModel):
    """
    FastAPI request payload schema for /chat.
    """
    messages: List[APIMessage] = Field(description="Sequential list of conversation messages")

class APIRecommendation(BaseModel):
    """
    FASTAPI schema representing a single assessment recommendation item.
    """
    name: str = Field(description="Name of the recommended assessment")
    url: str = Field(description="Direct URL link to the assessment page")
    test_type: str = Field(description="Type classification of the test (e.g., A, P, K)")

class ChatResponse(BaseModel):
    """
    FastAPI response schema for /chat.
    Matches the required assignment output structure EXACTLY.
    """
    reply: str = Field(description="The conversational text output from the assistant")
    recommendations: List[APIRecommendation] = Field(description="List of structured assessment matches")
    end_of_conversation: bool = Field(description="Flag indicating if the conversation has concluded")
