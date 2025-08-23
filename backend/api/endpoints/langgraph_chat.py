"""
LangGraph-based chat endpoint for PartSelect assistant
"""

from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
import logging
import asyncio
import uuid
from pathlib import Path

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from agents.orchestrator import get_orchestrator
from services.vector_store.setup import PartSelectVectorStore

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/langgraph", tags=["LangGraph Chat"])

class ChatMessage(BaseModel):
    role: str  # "user" or "assistant"
    content: str
    timestamp: Optional[str] = None

class ChatRequest(BaseModel):
    message: str
    thread_id: Optional[str] = None
    include_metadata: bool = False

class ChatResponse(BaseModel):
    response: str
    intent: Optional[str] = None
    confidence: float = 0.0
    thread_id: str
    processing_steps: List[str] = []
    metadata: Dict[str, Any] = {}
    error: Optional[str] = None

class ConversationHistoryResponse(BaseModel):
    thread_id: str
    messages: List[ChatMessage]

class SystemStatusResponse(BaseModel):
    status: str
    components: Dict[str, str]
    vector_db_stats: Dict[str, int] = {}

# Global orchestrator instance
orchestrator = None

@router.on_event("startup")
async def startup_event():
    """Initialize orchestrator on startup"""
    global orchestrator
    try:
        # Get the vector database path
        current_dir = Path(__file__).parent
        vector_db_path = current_dir.parent.parent / "services" / "vector_store" / "vector_db"
        
        orchestrator = get_orchestrator(str(vector_db_path))
        logger.info("LangGraph orchestrator initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize orchestrator: {str(e)}")

@router.post("/chat", response_model=ChatResponse)
async def chat_with_agent(request: ChatRequest) -> ChatResponse:
    """
    Chat with the PartSelect assistant using LangGraph agents
    """
    if orchestrator is None:
        raise HTTPException(status_code=500, detail="Orchestrator not initialized")
    
    # Generate thread ID if not provided
    thread_id = request.thread_id or str(uuid.uuid4())
    
    try:
        logger.info(f"Processing chat request for thread {thread_id}")
        
        # Process the query through the orchestrator
        result = await orchestrator.process_query(
            query=request.message,
            thread_id=thread_id
        )
        
        response = ChatResponse(
            response=result["response"],
            intent=result.get("intent"),
            confidence=result.get("confidence", 0.0),
            thread_id=thread_id,
            processing_steps=result.get("processing_steps", []),
            error=result.get("error")
        )
        
        # Include metadata if requested
        if request.include_metadata:
            response.metadata = result.get("metadata", {})
        
        logger.info(f"Chat request completed for thread {thread_id}")
        return response
        
    except Exception as e:
        logger.error(f"Error processing chat request: {str(e)}")
        raise HTTPException(
            status_code=500, 
            detail=f"Error processing request: {str(e)}"
        )

@router.get("/conversation/{thread_id}", response_model=ConversationHistoryResponse)
async def get_conversation_history(thread_id: str) -> ConversationHistoryResponse:
    """
    Get conversation history for a specific thread
    """
    if orchestrator is None:
        raise HTTPException(status_code=500, detail="Orchestrator not initialized")
    
    try:
        # Get conversation history from orchestrator
        history = orchestrator.get_conversation_history()
        
        # Convert to ChatMessage format
        messages = [
            ChatMessage(role=msg["role"], content=msg["content"])
            for msg in history
        ]
        
        return ConversationHistoryResponse(
            thread_id=thread_id,
            messages=messages
        )
        
    except Exception as e:
        logger.error(f"Error retrieving conversation history: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error retrieving conversation: {str(e)}"
        )

@router.delete("/conversation/{thread_id}")
async def reset_conversation(thread_id: str):
    """
    Reset conversation history for a thread
    """
    if orchestrator is None:
        raise HTTPException(status_code=500, detail="Orchestrator not initialized")
    
    try:
        orchestrator.reset_conversation()
        logger.info(f"Conversation reset for thread {thread_id}")
        
        return {"status": "success", "message": f"Conversation {thread_id} reset"}
        
    except Exception as e:
        logger.error(f"Error resetting conversation: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error resetting conversation: {str(e)}"
        )

@router.get("/status", response_model=SystemStatusResponse)
async def get_system_status() -> SystemStatusResponse:
    """
    Get system health status and statistics
    """
    if orchestrator is None:
        return SystemStatusResponse(
            status="error",
            components={"orchestrator": "not initialized"}
        )
    
    try:
        # Get health check from orchestrator
        health = await orchestrator.health_check()
        
        # Get vector database statistics
        vector_db_stats = {}
        try:
            # Get the vector database path
            current_dir = Path(__file__).parent
            vector_db_path = current_dir.parent.parent / "services" / "vector_store" / "vector_db"
            
            vector_store = PartSelectVectorStore(str(vector_db_path))
            vector_store.setup_collections()
            vector_db_stats = vector_store.get_collection_stats()
        except Exception as e:
            logger.warning(f"Could not get vector DB stats: {str(e)}")
        
        # Determine overall status
        status = "healthy"
        components = health.get("agents", {})
        components["orchestrator"] = health.get("orchestrator", "unknown")
        components["vector_db"] = health.get("vector_db", "unknown")
        
        # Check if any component is unhealthy
        for component, component_status in components.items():
            if "error" in component_status.lower() or component_status == "unknown":
                status = "degraded"
                break
        
        return SystemStatusResponse(
            status=status,
            components=components,
            vector_db_stats=vector_db_stats
        )
        
    except Exception as e:
        logger.error(f"Error getting system status: {str(e)}")
        return SystemStatusResponse(
            status="error",
            components={"system": f"error: {str(e)}"}
        )

@router.post("/initialize")
async def initialize_system(background_tasks: BackgroundTasks):
    """
    Initialize or reinitialize the system components
    """
    def _initialize():
        try:
            global orchestrator
            # Get the vector database path
            current_dir = Path(__file__).parent
            vector_db_path = current_dir.parent.parent / "services" / "vector_store" / "vector_db"
            
            orchestrator = get_orchestrator(str(vector_db_path))
            logger.info("System reinitialized successfully")
        except Exception as e:
            logger.error(f"Failed to reinitialize system: {str(e)}")
    
    background_tasks.add_task(_initialize)
    
    return {"status": "success", "message": "System initialization started"}

@router.post("/vector-db/setup")
async def setup_vector_database(background_tasks: BackgroundTasks):
    """
    Setup or refresh the vector database with latest data
    """
    def _setup_vector_db():
        try:
            # Get the data directory path
            current_dir = Path(__file__).parent
            data_dir = current_dir.parent.parent.parent / "scraping" / "data"
            vector_db_path = current_dir.parent.parent / "services" / "vector_store" / "vector_db"
            
            # Initialize vector store
            vector_store = PartSelectVectorStore(str(vector_db_path))
            vector_store.setup_collections()
            
            # Ingest data
            parts_file = data_dir / "all_parts.json"
            repairs_file = data_dir / "all_repairs.json"
            blogs_file = data_dir / "partselect_blogs.json"
            
            if parts_file.exists():
                vector_store.ingest_parts_data(str(parts_file))
            
            if repairs_file.exists():
                vector_store.ingest_repairs_data(str(repairs_file))
            
            if blogs_file.exists():
                vector_store.ingest_blogs_data(str(blogs_file))
            
            logger.info("Vector database setup completed")
            
        except Exception as e:
            logger.error(f"Failed to setup vector database: {str(e)}")
    
    background_tasks.add_task(_setup_vector_db)
    
    return {"status": "success", "message": "Vector database setup started"}

# Sample test queries for demonstration
@router.get("/sample-queries")
async def get_sample_queries():
    """
    Get sample queries that demonstrate the assistant's capabilities
    """
    return {
        "sample_queries": [
            {
                "category": "Part Search",
                "queries": [
                    "I need a water filter for my refrigerator",
                    "Show me dishwasher door seals",
                    "Find parts for Whirlpool appliances"
                ]
            },
            {
                "category": "Compatibility Check", 
                "queries": [
                    "Is part PS11752778 compatible with my WDT780SAEM1?",
                    "Will this water filter work with model number MFI2568AES?",
                    "Can I use part WP12345 in my GE dishwasher?"
                ]
            },
            {
                "category": "Troubleshooting",
                "queries": [
                    "My refrigerator ice maker is not working",
                    "The dishwasher is not draining water",
                    "Why is my fridge not cooling properly?"
                ]
            },
            {
                "category": "Installation Help",
                "queries": [
                    "How do I install part number PS11752778?",
                    "What tools do I need to replace a water filter?",
                    "Show me installation videos for dishwasher parts"
                ]
            }
        ]
    }
