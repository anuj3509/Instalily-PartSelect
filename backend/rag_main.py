"""
FastAPI main application for RAG-based PartSelect assistant
This replaces the LangGraph-based system with a more efficient RAG approach
"""

import sys
import os
from pathlib import Path

# Load environment variables from .env file
from dotenv import load_dotenv
load_dotenv()

# Add the backend directory to Python path for imports
backend_dir = Path(__file__).parent
sys.path.append(str(backend_dir))

import asyncio
import logging
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
import uuid

from agents.optimized_rag_agent import OptimizedRAGOrchestrator

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="PartSelect AI Assistant (RAG)", 
    version="2.0.0",
    description="RAG-powered assistant with real-time database queries"
)

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:3001", "http://localhost:8080"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global orchestrator instance
orchestrator = None

class ChatMessage(BaseModel):
    role: str
    content: str

class ChatRequest(BaseModel):
    message: str
    thread_id: Optional[str] = None
    conversation_history: Optional[List[ChatMessage]] = []

class ChatResponse(BaseModel):
    response: str
    thread_id: str
    conversation_history: List[ChatMessage]
    tools_used: Optional[List[str]] = []

@app.on_event("startup")
async def startup_event():
    """Initialize the RAG orchestrator on startup"""
    global orchestrator
    try:
        logger.info("Initializing RAG orchestrator...")
        orchestrator = OptimizedRAGOrchestrator()
        logger.info("PartSelect RAG orchestrator initialized successfully")
        
        # Test database connection
        logger.info("Testing database connection...")
        try:
            from database.database_manager import PartSelectDatabase
            db = PartSelectDatabase()
            stats = db.get_database_stats()
            logger.info(f"Database stats: {stats}")
        except ImportError as e:
            logger.warning(f"Could not import database manager: {e}")
            stats = {}
            db = None
        
        if stats and sum(stats.values()) == 0:
            logger.warning("Database appears to be empty. Loading data...")
            try:
                if db:
                    db.load_data_from_json()
                    logger.info("Data loaded successfully")
            except Exception as e:
                logger.error(f"Failed to load data: {e}")
        
    except Exception as e:
        logger.error(f"Failed to initialize RAG orchestrator: {e}")
        raise

@app.get("/")
async def root():
    return {
        "message": "PartSelect AI Assistant API (RAG-powered)", 
        "status": "online",
        "version": "2.0.0",
        "architecture": "RAG with real-time database queries",
        "features": [
            "Real-time parts database queries",
            "Accurate pricing and availability",
            "Actual PartSelect URLs",
            "Tool-based data retrieval",
            "No hallucinated information"
        ]
    }

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    try:
        if not orchestrator:
            return {"status": "unhealthy", "error": "Orchestrator not initialized"}
        
        # Simple health check - avoid problematic imports in health endpoint
        return {
            "status": "healthy", 
            "service": "rag-chat", 
            "version": "2.0.0",
            "orchestrator": "initialized"
        }
    except Exception as e:
        return {"status": "unhealthy", "error": str(e)}

@app.post("/chat", response_model=ChatResponse)
async def chat_endpoint(request: ChatRequest):
    """Main chat endpoint using RAG orchestrator with database tools"""
    try:
        if not orchestrator:
            raise HTTPException(status_code=500, detail="RAG orchestrator not initialized")
        
        # Use provided thread_id or let orchestrator create one
        thread_id = request.thread_id
        
        logger.info(f"Processing message: {request.message[:100]}... (Thread: {thread_id})")
        
        # Process the message with optimized RAG agent
        result = await orchestrator.process_query(request.message, thread_id)
        
        # Get actual thread_id from result (may be created by orchestrator)
        actual_thread_id = result.get("thread_id", thread_id or str(uuid.uuid4()))
        
        # Convert conversation history to the expected format
        conversation_history = [
            ChatMessage(role=msg["role"], content=msg["content"])
            for msg in result.get("conversation_history", [])
        ]
        
        # Log cache efficiency info
        stats = result.get("conversation_stats", {})
        if stats:
            logger.info(f"Conversation stats - Messages: {stats.get('total_messages', 0)}, "
                       f"Cache efficiency: {stats.get('cache_efficiency', 'Unknown')}, "
                       f"Estimated tokens: {stats.get('estimated_tokens', 0)}")
        
        return ChatResponse(
            response=result["response"],
            thread_id=actual_thread_id,
            conversation_history=conversation_history,
            tools_used=[]  # No tools used in optimized approach
        )
        
    except Exception as e:
        logger.error(f"Error in chat endpoint: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/new-chat")
async def new_chat():
    """Start a new chat conversation"""
    try:
        if not orchestrator:
            raise HTTPException(status_code=500, detail="RAG orchestrator not initialized")
        
        # Create new conversation thread
        thread_id = orchestrator.reset_conversation()
        
        # Get initial conversation with welcome message
        from conversation.memory_manager import get_memory_manager
        memory_manager = get_memory_manager()
        conversation_history = [
            ChatMessage(role=msg["role"], content=msg["content"])
            for msg in memory_manager.get_conversation_history(thread_id)
        ]
        
        # Get welcome message
        welcome_message = """Welcome to PartSelect AI Assistant! I specialize in refrigerator and dishwasher parts and can help you with:

✓ Finding the right appliance parts
✓ Checking part compatibility  
✓ Troubleshooting common issues
✓ Providing repair guidance

What can I help you with today?"""
        
        logger.info(f"New chat started with thread ID: {thread_id}")
        
        return ChatResponse(
            response=welcome_message,
            thread_id=thread_id,
            conversation_history=conversation_history,
            tools_used=[]
        )
        
    except Exception as e:
        logger.error(f"Error in new chat endpoint: {e}")
        raise HTTPException(status_code=500, detail=str(e))

class RegenerateRequest(BaseModel):
    thread_id: str

@app.post("/regenerate")
async def regenerate_response(request: RegenerateRequest):
    """Regenerate the last response using RAG agent"""
    try:
        if not orchestrator:
            raise HTTPException(status_code=500, detail="RAG orchestrator not initialized")
        
        result = await orchestrator.regenerate_last_response(request.thread_id)
        
        # Convert conversation history to the expected format
        conversation_history = [
            ChatMessage(role=msg["role"], content=msg["content"])
            for msg in result.get("conversation_history", [])
        ]
        
        logger.info(f"Response regenerated for thread: {request.thread_id}")
        
        return ChatResponse(
            response=result["response"],
            thread_id=result.get("thread_id", request.thread_id),
            conversation_history=conversation_history,
            tools_used=[]  # No tools used in optimized approach
        )
        
    except Exception as e:
        logger.error(f"Error in regenerate endpoint: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/database/stats")
async def get_database_stats():
    """Get database statistics for debugging"""
    try:
        from tools.database_tools import PartSelectDatabaseTools
        tools = PartSelectDatabaseTools()
        stats = tools.db.get_database_stats()
        
        # Get additional info
        brands = tools.db.get_brands()
        categories = tools.db.get_categories()
        price_range = tools.db.get_price_range()
        
        return {
            "database_stats": stats,
            "status": "healthy" if sum(stats.values()) > 0 else "empty",
            "total_records": sum(stats.values()),
            "available_brands": len(brands),
            "available_categories": len(categories),
            "price_range": {
                "min": price_range[0],
                "max": price_range[1]
            }
        }
        
    except Exception as e:
        logger.error(f"Error getting database stats: {e}")
        return {"error": str(e), "status": "error"}

@app.get("/tools/available")
async def get_available_tools():
    """Get list of available tools for debugging"""
    try:
        from tools.database_tools import AVAILABLE_TOOLS
        
        tools_info = {}
        for tool_name, tool_data in AVAILABLE_TOOLS.items():
            tools_info[tool_name] = {
                "description": tool_data["description"],
                "parameters": list(tool_data["parameters"]["properties"].keys()),
                "required_parameters": tool_data["parameters"].get("required", [])
            }
        
        return {
            "available_tools": tools_info,
            "total_tools": len(tools_info),
            "tool_categories": {
                "search": ["search_parts", "search_repair_guides", "search_blog_content"],
                "lookup": ["get_part_details", "search_compatible_parts"],
                "metadata": ["get_available_brands", "get_price_range"]
            }
        }
        
    except Exception as e:
        logger.error(f"Error getting available tools: {e}")
        return {"error": str(e)}

@app.get("/conversations")
async def get_all_conversations():
    """Get summary of all active conversations"""
    try:
        from conversation.memory_manager import get_memory_manager
        memory_manager = get_memory_manager()
        
        conversations = memory_manager.get_all_conversations()
        
        return {
            "active_conversations": conversations,
            "total_conversations": len(conversations)
        }
        
    except Exception as e:
        logger.error(f"Error getting conversations: {e}")
        return {"error": str(e)}

@app.get("/conversation/{thread_id}/stats")
async def get_conversation_stats(thread_id: str):
    """Get detailed stats for a specific conversation"""
    try:
        if not orchestrator:
            raise HTTPException(status_code=500, detail="RAG orchestrator not initialized")
        
        stats = orchestrator.get_conversation_stats(thread_id)
        
        if not stats:
            raise HTTPException(status_code=404, detail="Conversation not found")
        
        return stats
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting conversation stats: {e}")
        return {"error": str(e)}

@app.post("/cleanup-conversations")
async def cleanup_old_conversations(max_age_hours: int = 24):
    """Clean up old conversations"""
    try:
        if not orchestrator:
            raise HTTPException(status_code=500, detail="RAG orchestrator not initialized")
        
        cleaned_count = orchestrator.cleanup_old_conversations(max_age_hours)
        
        return {
            "status": "success",
            "cleaned_conversations": cleaned_count,
            "message": f"Cleaned up {cleaned_count} conversations older than {max_age_hours} hours"
        }
        
    except Exception as e:
        logger.error(f"Error cleaning up conversations: {e}")
        return {"error": str(e)}

@app.post("/database/initialize")
async def initialize_database():
    """Initialize database with data from JSON files"""
    try:
        from database.database_manager import PartSelectDatabase
        db = PartSelectDatabase()
        
        # Load data
        db.load_data_from_json()
        
        # Get updated stats
        stats = db.get_database_stats()
        
        return {
            "status": "success",
            "message": "Database initialized successfully",
            "database_stats": stats,
            "total_records": sum(stats.values())
        }
        
    except Exception as e:
        logger.error(f"Error initializing database: {e}")
        return {"status": "error", "error": str(e)}

@app.get("/sample-queries")
async def get_sample_queries():
    """Get sample queries that demonstrate the RAG assistant's capabilities"""
    return {
        "sample_queries": [
            {
                "category": "Part Search",
                "description": "Search for specific parts with real pricing and availability",
                "queries": [
                    "I need a water filter for my refrigerator",
                    "Show me dishwasher door seals under $50",
                    "Find Whirlpool refrigerator parts in stock"
                ]
            },
            {
                "category": "Compatibility Check", 
                "description": "Check part compatibility with specific models",
                "queries": [
                    "What parts are compatible with model GE GSS25GSHSS?",
                    "Find parts for Whirlpool model WDT780SAEM1",
                    "Show compatible parts for my Frigidaire dishwasher model FFCD2413US"
                ]
            },
            {
                "category": "Troubleshooting",
                "description": "Get repair guides with real video links and part recommendations",
                "queries": [
                    "My refrigerator ice maker is not working",
                    "The dishwasher is leaking water",
                    "Why is my fridge not cooling properly?"
                ]
            },
            {
                "category": "Educational Content",
                "description": "Find blog articles and maintenance guides",
                "queries": [
                    "How to clean a dishwasher filter",
                    "Refrigerator maintenance tips",
                    "How to replace a water filter"
                ]
            }
        ],
        "note": "All responses include real PartSelect data with actual URLs, prices, and part numbers."
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8080)
