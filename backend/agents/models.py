"""
Pydantic models for the PartSelect agent system
"""

from typing import List, Dict, Any, Optional, Literal
from pydantic import BaseModel, Field
from enum import Enum

class QueryIntent(str, Enum):
    """Types of user intents"""
    PART_SEARCH = "part_search"
    COMPATIBILITY_CHECK = "compatibility_check"
    TROUBLESHOOTING = "troubleshooting"
    INSTALLATION_HELP = "installation_help"
    OUT_OF_SCOPE = "out_of_scope"

class AgentState(BaseModel):
    """State shared between agents in the LangGraph"""
    # Input
    user_query: str
    conversation_history: List[Dict[str, str]] = Field(default_factory=list)
    
    # Analysis results
    intent: Optional[QueryIntent] = None
    extracted_entities: Dict[str, Any] = Field(default_factory=dict)
    confidence_score: float = 0.0
    
    # Retrieval results
    parts_results: List[Dict[str, Any]] = Field(default_factory=list)
    repairs_results: List[Dict[str, Any]] = Field(default_factory=list)
    blogs_results: List[Dict[str, Any]] = Field(default_factory=list)
    
    # Generated response
    response: str = ""
    
    # Control flow
    needs_parts_search: bool = False
    needs_compatibility_check: bool = False
    needs_troubleshooting: bool = False
    is_complete: bool = False
    
    # Metadata
    processing_steps: List[str] = Field(default_factory=list)
    error_message: Optional[str] = None

class IntentAnalysisResult(BaseModel):
    """Result of intent classification"""
    intent: QueryIntent = Field(description="Classified intent of the user query")
    confidence: float = Field(description="Confidence score between 0-1")
    extracted_entities: Dict[str, Any] = Field(
        default_factory=dict,
        description="Extracted entities like part numbers, model numbers, symptoms"
    )
    reasoning: str = Field(description="Explanation of the classification decision")

class VectorSearchResult(BaseModel):
    """Result from vector database search"""
    documents: List[str] = Field(description="Retrieved document texts")
    metadatas: List[Dict[str, Any]] = Field(description="Associated metadata")
    distances: List[float] = Field(description="Similarity distances")
    relevance_scores: List[float] = Field(description="Relevance scores after filtering")

class CompatibilityCheckResult(BaseModel):
    """Result of compatibility checking"""
    is_compatible: Optional[bool] = Field(description="Whether the part is compatible")
    confidence: float = Field(description="Confidence in the compatibility assessment")
    compatibility_url: Optional[str] = Field(description="URL for manual verification")
    explanation: str = Field(description="Explanation of compatibility determination")

class ResponseQuality(BaseModel):
    """Assessment of response quality"""
    is_helpful: bool = Field(description="Whether the response is helpful")
    is_accurate: bool = Field(description="Whether the response appears accurate")
    is_on_topic: bool = Field(description="Whether the response stays on topic")
    completeness_score: float = Field(description="How complete the response is (0-1)")
    improvement_suggestions: List[str] = Field(
        default_factory=list,
        description="Suggestions for improving the response"
    )

class PartSearchRequest(BaseModel):
    """Request for parts search"""
    search_query: str = Field(description="Natural language search query")
    category_filter: Optional[str] = Field(description="Category to filter by")
    brand_filter: Optional[str] = Field(description="Brand to filter by")
    max_results: int = Field(default=5, description="Maximum number of results")

class TroubleshootingRequest(BaseModel):
    """Request for troubleshooting assistance"""
    appliance_type: str = Field(description="Type of appliance (refrigerator/dishwasher)")
    symptom_description: str = Field(description="Description of the problem")
    model_number: Optional[str] = Field(description="Model number if provided")
    brand: Optional[str] = Field(description="Brand if provided")

class AgentStrategy(BaseModel):
    """AI-driven strategy for handling a query"""
    approach: str = Field(description="Overall approach to take (e.g., 'comprehensive_search', 'quick_lookup', 'troubleshooting_flow')")
    agents_needed: List[str] = Field(description="List of agents needed for this query")
    parallel_execution: bool = Field(description="Whether agents can run in parallel")
    confidence_threshold: float = Field(description="Minimum confidence needed before responding")
    reasoning: str = Field(description="Explanation of why this strategy was chosen")

class ResponseValidation(BaseModel):
    """Validation result for generated responses"""
    is_appropriate: bool = Field(description="Whether response is appropriate for appliance parts assistant")
    stays_in_scope: bool = Field(description="Whether response stays within refrigerator/dishwasher domain")
    has_hallucination: bool = Field(description="Whether response contains hallucinated information")
    feedback: Optional[str] = Field(description="Feedback for improvement if validation fails")

class AgentResponse(BaseModel):
    """Response from an individual agent"""
    agent_name: str = Field(description="Name of the agent")
    success: bool = Field(description="Whether the agent completed successfully")
    results: Dict[str, Any] = Field(description="Results produced by the agent")
    error_message: Optional[str] = Field(default=None, description="Error message if failed")
    processing_time: float = Field(description="Time taken to process")
