from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any

class Assessment(BaseModel):
    """
    Core Domain Model representing an SHL Assessment.
    Matches the fields scraped from the SHL Individual Test Solutions catalog.
    """
    name: str
    description: str
    url: str
    category: str = ""
    skills: List[str] = Field(default_factory=list)
    job_roles: List[str] = Field(default_factory=list)
    duration: Optional[int] = None
    remote_testing_support: bool = False
    adaptive: bool = False
    languages: List[str] = Field(default_factory=list)
    test_type: List[str] = Field(default_factory=list)  # List of codes like ["P", "K", "A"]
    metadata: Dict[str, Any] = Field(default_factory=dict)

class ConversationState(BaseModel):
    """
    Represents the reconstructed criteria state from the chat history.
    """
    job_role: Optional[str] = None
    experience_level: Optional[str] = None
    required_skills: List[str] = Field(default_factory=list)
    test_types: List[str] = Field(default_factory=list)
    remote_testing: Optional[bool] = None
    adaptive: Optional[bool] = None

class Message(BaseModel):
    """
    Represents a chat message.
    """
    role: str  # "user" or "assistant"
    content: str
