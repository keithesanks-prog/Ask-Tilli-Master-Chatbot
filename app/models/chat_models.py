"""
Chat API Models

Pydantic models for the /chat endpoint that mirrors the emt-api structure.
"""
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field


class ChatHistoryMessage(BaseModel):
    """
    Represents a single message in conversation history.
    
    Attributes:
        role: Role of the message sender (e.g., "user", "assistant", "system")
        text: Content of the message
    """
    role: str = Field(..., description="Role of the message sender (user/assistant/system)")
    text: str = Field(..., description="Content of the message")


class ChatRequest(BaseModel):
    """
    Request model for the /chat endpoint.
    
    Matches the emt-api chat() function input structure:
    {
        "message": "user's question",
        "scores": {...},
        "history": [...]
    }
    
    Attributes:
        message: The user's current message/question
        scores: SEL assessment scores data structure
        history: Previous conversation messages
    """
    message: str = Field(..., description="The user's current message or question")
    scores: Dict[str, Any] = Field(
        default_factory=dict,
        description="SEL assessment scores data (supports 4 assessments: child, parent, teacher_report, teacher_survey)"
    )
    history: List[ChatHistoryMessage] = Field(
        default_factory=list,
        description="Previous conversation history"
    )


class ChatResponse(BaseModel):
    """
    Response model for the /chat endpoint.
    
    Matches the emt-api chat() function output: plain text response.
    
    Attributes:
        response: The generated text response from the LLM
    """
    response: str = Field(..., description="Generated response from the LLM")
