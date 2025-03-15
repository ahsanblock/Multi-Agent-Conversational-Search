from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime

class SearchQuery(BaseModel):
    """Search query model"""
    query: str = Field(..., description="The user's search query")
    user_id: Optional[str] = Field(None, description="User identifier for personalization")
    filters: Optional[Dict[str, Any]] = Field(
        default={},
        description="Optional filters for the search"
    )
    context: Optional[Dict[str, Any]] = Field(
        default={},
        description="Additional context for the search"
    )

class Product(BaseModel):
    """Product model"""
    id: str
    name: str
    description: str
    price: float
    category: str
    attributes: Dict[str, Any]
    score: Optional[float] = None
    vector: Optional[List[float]] = None

class SearchResult(BaseModel):
    """Individual search result"""
    product: Product
    relevance_score: float
    personalization_score: Optional[float] = None
    explanation: Optional[str] = None

class SearchResponse(BaseModel):
    """Search response model"""
    query: str
    products: List[Product]
    ai_response: str
    total_results: int
    processing_time: float = Field(default=0.0)
    filters_applied: Dict[str, Any] = Field(default_factory=dict)
    suggestions: Optional[List[str]] = None
    debug_info: Optional[Dict[str, Any]] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)

class UserProfile(BaseModel):
    """User profile for personalization"""
    user_id: str
    preferences: Dict[str, Any]
    search_history: List[Dict[str, Any]]
    last_updated: datetime = Field(default_factory=datetime.utcnow)

class AgentTask(BaseModel):
    """Model for agent tasks"""
    task_id: str
    agent_name: str
    input_data: Dict[str, Any]
    output_data: Optional[Dict[str, Any]] = None
    status: str
    started_at: datetime = Field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = None
    error: Optional[str] = None 