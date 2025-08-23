"""
Optimized RAG agent that fetches data first, then makes a single LLM call
This approach eliminates the need for tool calling and reduces LLM calls to one
"""

import json
import logging
from typing import Dict, List, Any, Optional
from openai import AsyncOpenAI
import instructor
from pathlib import Path
from dotenv import load_dotenv
import os
import re

# Load environment variables
current_dir = Path(__file__).parent
project_root = current_dir.parent.parent
env_path = project_root / '.env'
load_dotenv(env_path)

from database.database_manager import PartSelectDatabase
from services.vector_store.setup import PartSelectVectorStore

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class OptimizedRAGAgent:
    """
    Optimized RAG agent that:
    1. First queries read-optimized database
    2. Uses vector DB for additional context if needed
    3. Makes a single LLM call to generate response
    """
    
    def __init__(self):
        # Initialize DeepSeek client (no instructor needed for simple completion)
        self.client = AsyncOpenAI(
            api_key=os.getenv("DEEPSEEK_API_KEY"),
            base_url="https://api.deepseek.com"
        )
        
        # Initialize databases
        self.read_db = PartSelectDatabase()
        
        # Initialize vector DB
        vector_db_path = Path(__file__).parent.parent / "services" / "vector_store" / "vector_db"
        self.vector_db = PartSelectVectorStore(str(vector_db_path))
        self.vector_db.setup_collections()
        
        # System prompt for single LLM call
        self.system_prompt = """You are an expert PartSelect AI Assistant specializing in refrigerator and dishwasher parts, repairs, and troubleshooting.

**IMPORTANT**: You will receive REAL data from our database. Use ONLY this data in your responses. Do not generate fake URLs, part numbers, or prices.

**RESPONSE GUIDELINES:**

**URL HANDLING:**
- ONLY use URLs provided in the data
- NEVER generate or guess URLs
- If no URL is provided, don't mention URLs

**FORMATTING:**
- Use proper markdown with `- ` for bullet points
- Add blank lines before **Next Step:** sections
- Include real prices when available
- Provide actual part numbers for ordering

**RESPONSE STRUCTURE:**

For **Troubleshooting** queries:
```
## [Symptom] - [Appliance Type]

**Troubleshooting Guide:**
[Include repair guide description if available]

**Repair Video:**
[Include YouTube video link if available]

**Most Likely Causes:**
- [Real cause from repair guide]
- [Real cause from repair guide]

**Recommended Parts:**
- [Real part with price and part number]
- [Real part with price and part number]

**Difficulty:** [Real difficulty rating from repair guide]

**Next Step:**
Watch the repair video: [YouTube URL]
Visit: [Real detail URL] for complete troubleshooting steps
```

For **Part Search** queries:
```
## [Part Name] - [Brand]

**Part Details:**
- Part Number: [Real part number]
- Price: $[Real price]
- Brand: [Real brand]
- Availability: [Real stock status]

**Description:**
[Real product description]

**Installation:**
[Real installation guidance if available]

**Next Step:**
Visit: [Real product URL] to order this part.
```

For **Troubleshooting** queries:
```
## [Symptom] - [Appliance Type]

**Most Likely Causes:**
- [Real cause from database]
- [Real cause from database]

**Recommended Parts:**
- [Real part with price and part number]

**Repair Guide:**
[Real repair video URL if available]

**Difficulty:** [Real difficulty rating]

**Next Step:**
[Specific action with real URLs]
```

**CONTENT GUIDELINES:**
- **CRITICAL: For troubleshooting queries, ALWAYS include repair guide information and YouTube video links when available**
- **CRITICAL: For installation queries, ALWAYS include installation video links when available**
- **MUST INCLUDE: Any "Installation Video" URLs provided in the part data**
- Keep responses 300-600 words based on complexity
- Be thorough but concise
- Always include actionable next steps
- Stay within refrigerator/dishwasher domain
- If no relevant data found, say so honestly

**Out of Scope:**
For other appliances or non-repair topics: "I specialize in refrigerator and dishwasher parts and repairs. For [topic], contact PartSelect customer service at 1-866-319-8402."
"""

    async def process_query(self, user_query: str, conversation_history: List[Dict[str, str]] = None) -> Dict[str, Any]:
        """
        Process query with optimized RAG approach:
        1. Fetch data from read-optimized DB first
        2. Use vector DB for additional context if needed  
        3. Single LLM call with all data
        """
        try:
            logger.info(f"Processing query: {user_query[:100]}...")
            
            # Step 1: Analyze query type and extract key terms
            query_info = await self._analyze_query(user_query)
            
            # Step 2: Fetch data from read-optimized database (primary)
            primary_data = await self._fetch_primary_data(query_info)
            
            # Step 3: Fetch additional context from vector DB if needed
            additional_context = await self._fetch_vector_context(query_info, primary_data)
            
            # Step 4: Combine all data
            combined_data = self._combine_data(primary_data, additional_context)
            
            # Step 5: Single LLM call with all data
            response = await self._generate_response(user_query, combined_data, conversation_history)
            
            return {
                "success": True,
                "response": response,
                "data_sources": {
                    "primary_db_results": len(primary_data.get("parts", [])) + len(primary_data.get("repairs", [])),
                    "vector_db_results": len(additional_context.get("parts", [])) + len(additional_context.get("repairs", [])),
                    "total_sources": len(combined_data.get("all_sources", []))
                },
                "query_type": query_info["type"],
                "message": "Query processed successfully"
            }
            
        except Exception as e:
            logger.error(f"Error processing query: {e}")
            return {
                "success": False,
                "response": "I apologize, but I encountered an error processing your request. Please try again or contact customer service at 1-866-319-8402.",
                "error": str(e),
                "message": "Failed to process query"
            }
    
    async def _analyze_query(self, query: str) -> Dict[str, Any]:
        """Analyze query using LLM to determine type and extract key terms intelligently"""
        try:
            # Use LLM for intelligent query analysis
            return await self._llm_analyze_query(query)
        except Exception as e:
            logger.warning(f"LLM query analysis failed, falling back to rule-based: {e}")
            # Fallback to rule-based analysis
            return self._rule_based_analyze_query(query)
    
    async def _llm_analyze_query(self, query: str) -> Dict[str, Any]:
        """Use LLM to analyze query intelligently"""
        analysis_prompt = """You are a query analyzer for an appliance parts and repair system. Analyze the user's query and return a JSON response with the following structure:

{
    "type": "query_type",
    "appliance_type": "appliance_type_or_null",
    "key_terms": ["extracted", "terms"],
    "confidence": 0.95,
    "search_strategy": "recommended_search_approach"
}

Query Types:
- "specific_part": Looking for a specific part by part number (PS123, W10234, etc.)
- "compatibility": Asking about part compatibility with models/appliances
- "troubleshooting": Reporting problems, symptoms, or asking for repairs
- "educational": How-to questions, installation guides, maintenance
- "part_search": General part search by description/function

Appliance Types:
- "refrigerator" (includes fridge, ice maker, freezer)
- "dishwasher"
- null (if not specified or other appliance)

Key Terms to Extract:
- Part numbers (PS123, W10234, etc.)
- Model numbers (KFIS29PBMS, GE123, etc.)
- Brand names (Whirlpool, GE, Samsung, LG, etc.)
- Part types (filter, seal, motor, pump, etc.)
- Symptoms (leaking, not working, noisy, etc.)
- Component names (door, dispenser, ice maker, etc.)

Search Strategy:
- "exact_match": For specific part numbers
- "compatibility_search": For model compatibility queries
- "symptom_based": For troubleshooting queries
- "semantic_search": For general part searches
- "educational_content": For how-to queries

Return ONLY valid JSON. Be precise and extract all relevant terms."""

        messages = [
            {"role": "system", "content": analysis_prompt},
            {"role": "user", "content": f"Analyze this query: {query}"}
        ]

        response = await self.client.chat.completions.create(
            model="deepseek-chat",
            messages=messages,
            temperature=0.1,  # Low temperature for consistent analysis
            max_tokens=500,
            response_format={"type": "json_object"}
        )

        # Parse JSON response
        analysis = json.loads(response.choices[0].message.content)
        
        # Add original query
        analysis["original_query"] = query
        
        # Validate required fields
        if "type" not in analysis:
            analysis["type"] = "part_search"
        if "key_terms" not in analysis:
            analysis["key_terms"] = []
        if "appliance_type" not in analysis:
            analysis["appliance_type"] = None
            
        logger.info(f"LLM query analysis: {analysis['type']} | {len(analysis['key_terms'])} terms | confidence: {analysis.get('confidence', 'N/A')}")
        return analysis

    def _rule_based_analyze_query(self, query: str) -> Dict[str, Any]:
        """Fallback rule-based query analysis (original method)"""
        query_lower = query.lower()
        
        # Determine query type
        if any(word in query_lower for word in ["part number", "ps", "model"]) and re.search(r'\b[A-Z]{2}\d+\b|\bPS\d+\b', query):
            query_type = "specific_part"
        elif any(word in query_lower for word in ["compatible", "compatibility", "model", "work with"]):
            query_type = "compatibility"
        elif any(word in query_lower for word in ["not working", "not making", "broken", "leaking", "problem", "issue", "troubleshoot", "repair", "fix", "won't work", "doesn't work", "stopped working"]):
            query_type = "troubleshooting"
        elif any(word in query_lower for word in ["how to", "install", "replace", "maintenance", "clean"]):
            query_type = "educational"
        else:
            query_type = "part_search"
        
        # Extract appliance type
        appliance_type = None
        if "refrigerator" in query_lower or "fridge" in query_lower:
            appliance_type = "refrigerator"
        elif "dishwasher" in query_lower:
            appliance_type = "dishwasher"
        
        # Extract key terms
        key_terms = []
        
        # Extract part numbers
        part_numbers = re.findall(r'\b(?:PS\d+|[A-Z]{2}\d+|W\d+|[A-Z]\d+[A-Z]+\d*)\b', query)
        key_terms.extend(part_numbers)
        
        # Extract model numbers
        model_numbers = re.findall(r'\b[A-Z]{2,}\d+[A-Z]*\d*\b', query)
        key_terms.extend(model_numbers)
        
        # Extract common part types
        part_types = ["filter", "seal", "door", "pump", "motor", "valve", "hose", "gasket", "dispenser", "ice maker"]
        for part_type in part_types:
            if part_type in query_lower:
                key_terms.append(part_type)
        
        # Extract brands
        brands = ["whirlpool", "ge", "frigidaire", "kenmore", "samsung", "lg", "maytag", "bosch"]
        for brand in brands:
            if brand in query_lower:
                key_terms.append(brand)
        
        return {
            "type": query_type,
            "appliance_type": appliance_type,
            "key_terms": list(set(key_terms)),  # Remove duplicates
            "original_query": query,
            "confidence": 0.8,  # Rule-based has good but not perfect confidence
            "search_strategy": "rule_based"
        }
    
    async def _fetch_primary_data(self, query_info: Dict[str, Any]) -> Dict[str, Any]:
        """Fetch data from read-optimized database first"""
        primary_data = {"parts": [], "repairs": [], "blogs": []}
        
        try:
            query_type = query_info["type"]
            key_terms = query_info["key_terms"]
            appliance_type = query_info["appliance_type"]
            
            # Build search query - for troubleshooting, extract key symptoms and components
            if query_type == "troubleshooting":
                # Extract key component and symptom terms for better matching
                troubleshooting_terms = []
                for term in key_terms:
                    if term.lower() not in ["ge", "whirlpool", "samsung", "lg", "frigidaire", "kenmore", "bosch", "maytag"]:  # Skip all brand names for troubleshooting
                        troubleshooting_terms.append(term)
                
                # For troubleshooting, focus on component names rather than problem keywords
                # Problem keywords like "not working" make FTS searches too restrictive
                
                search_query = " ".join(troubleshooting_terms) if troubleshooting_terms else (appliance_type or "appliance")
            else:
                search_query = " ".join(key_terms) if key_terms else query_info["original_query"]
            
            if query_type == "specific_part" and key_terms:
                # Look for specific part by part number
                for term in key_terms:
                    if re.match(r'PS\d+', term):
                        part = self.read_db.get_part_by_number(term)
                        if part:
                            primary_data["parts"].append(part)
            
            elif query_type == "compatibility" and key_terms:
                # Look for compatible parts by model number
                for term in key_terms:
                    if re.match(r'[A-Z]{2,}\d+', term):  # Model number pattern
                        compatible_parts = self.read_db.search_compatible_parts(term, appliance_type)
                        primary_data["parts"].extend(compatible_parts)
            
            elif query_type == "troubleshooting":
                # Search repair guides first
                repairs = self.read_db.search_repairs(search_query, appliance_type, limit=5)
                primary_data["repairs"].extend(repairs)
                
                # Also search for related parts to provide comprehensive troubleshooting
                filters = {}
                if appliance_type:
                    filters["category"] = appliance_type
                parts = self.read_db.search_parts(search_query, limit=5, filters=filters)
                primary_data["parts"].extend(parts)
            
            elif query_type == "educational":
                # Search blog content
                blogs = self.read_db.search_blogs(search_query, limit=3)
                primary_data["blogs"].extend(blogs)
                
                # If educational query mentions specific part numbers, also fetch part data
                for term in key_terms:
                    if re.match(r'PS\d+', term):
                        part = self.read_db.get_part_by_number(term)
                        if part:
                            primary_data["parts"].append(part)
            
            else:
                # General part search
                filters = {}
                if appliance_type:
                    filters["category"] = appliance_type
                
                # Extract brand filter
                for term in key_terms:
                    if term.lower() in ["whirlpool", "ge", "frigidaire", "kenmore", "samsung", "lg", "maytag", "bosch"]:
                        filters["brand"] = term.title()
                        break
                
                parts = self.read_db.search_parts(search_query, limit=10, filters=filters)
                primary_data["parts"].extend(parts)
            
            logger.info(f"Primary DB results: {len(primary_data['parts'])} parts, {len(primary_data['repairs'])} repairs, {len(primary_data['blogs'])} blogs")
            
        except Exception as e:
            logger.error(f"Error fetching primary data: {e}")
        
        return primary_data
    
    async def _fetch_vector_context(self, query_info: Dict[str, Any], primary_data: Dict[str, Any]) -> Dict[str, Any]:
        """Fetch additional context from vector DB if primary data is insufficient"""
        additional_context = {"parts": [], "repairs": [], "blogs": []}
        
        try:
            # Only use vector DB if primary data is limited
            total_primary_results = len(primary_data["parts"]) + len(primary_data["repairs"]) + len(primary_data["blogs"])
            
            if total_primary_results < 3:  # Need more context
                query = query_info["original_query"]
                
                # Search vector collections for additional context
                if query_info["type"] in ["part_search", "specific_part", "compatibility"]:
                    # Search parts collection
                    try:
                        parts_results = self.vector_db.parts_collection.query(
                            query_texts=[query],
                            n_results=5
                        )
                        
                        # Convert vector results to structured format
                        if parts_results["documents"]:
                            for i, doc in enumerate(parts_results["documents"][0]):
                                metadata = parts_results["metadatas"][0][i] if parts_results["metadatas"] else {}
                                additional_context["parts"].append({
                                    "content": doc,
                                    "metadata": metadata,
                                    "source": "vector_db"
                                })
                    except Exception as e:
                        logger.warning(f"Vector search for parts failed: {e}")
                
                if query_info["type"] in ["troubleshooting", "educational"]:
                    # Search repairs and blogs collections
                    try:
                        repairs_results = self.vector_db.repairs_collection.query(
                            query_texts=[query],
                            n_results=3
                        )
                        
                        if repairs_results["documents"]:
                            for i, doc in enumerate(repairs_results["documents"][0]):
                                metadata = repairs_results["metadatas"][0][i] if repairs_results["metadatas"] else {}
                                additional_context["repairs"].append({
                                    "content": doc,
                                    "metadata": metadata,
                                    "source": "vector_db"
                                })
                    except Exception as e:
                        logger.warning(f"Vector search for repairs failed: {e}")
                
                logger.info(f"Vector DB additional context: {len(additional_context['parts'])} parts, {len(additional_context['repairs'])} repairs")
        
        except Exception as e:
            logger.error(f"Error fetching vector context: {e}")
        
        return additional_context
    
    def _combine_data(self, primary_data: Dict[str, Any], additional_context: Dict[str, Any]) -> Dict[str, Any]:
        """Combine data from both sources"""
        combined = {
            "primary_parts": primary_data.get("parts", []),
            "primary_repairs": primary_data.get("repairs", []),
            "primary_blogs": primary_data.get("blogs", []),
            "additional_parts": additional_context.get("parts", []),
            "additional_repairs": additional_context.get("repairs", []),
            "additional_blogs": additional_context.get("blogs", []),
            "all_sources": []
        }
        
        # Create summary of all sources
        for part in primary_data.get("parts", []):
            combined["all_sources"].append(f"Part: {part.get('name', 'Unknown')} ({part.get('part_number', 'N/A')}) - ${part.get('price', 'N/A')}")
        
        for repair in primary_data.get("repairs", []):
            combined["all_sources"].append(f"Repair: {repair.get('symptom', 'Unknown')} - {repair.get('appliance_type', 'Unknown')}")
        
        for blog in primary_data.get("blogs", []):
            combined["all_sources"].append(f"Article: {blog.get('title', 'Unknown')}")
        
        return combined
    
    async def _generate_response(self, user_query: str, combined_data: Dict[str, Any], conversation_history: List[Dict[str, str]] = None) -> str:
        """Generate response with single DeepSeek LLM call using all fetched data"""
        try:
            # Build context from data
            context = self._build_context_string(combined_data)
            
            # Build messages for DeepSeek with context caching optimization
            messages = [{"role": "system", "content": self.system_prompt}]
            
            # Add conversation history if provided (this enables context caching)
            if conversation_history:
                messages.extend(conversation_history)
            
            # Add current query with context
            user_message = f"""User Query: {user_query}

Available Data from Database:
{context}

CRITICAL INSTRUCTIONS - YOU MUST FOLLOW THESE:
1. ALWAYS check for REPAIR GUIDES in the data above - if ANY exist, you MUST use them
2. NEVER say "I don't have access to specific troubleshooting guides" if repair guides are provided
3. If you see "Repair Video:" or "YouTube" links, you MUST include them in your response
4. Structure troubleshooting responses with: Repair guides first, then common causes, then parts
5. Use ONLY the real data provided above - no generic responses

MANDATORY: If repair guides exist in the data above, use them to answer the troubleshooting question."""
            
            messages.append({"role": "user", "content": user_message})
            
            # Single DeepSeek LLM call with context caching
            response = await self.client.chat.completions.create(
                model="deepseek-chat",
                messages=messages,
                temperature=1.0,  # Optimal for factual/technical responses (parts, repairs, troubleshooting)
                max_tokens=2000,
                stream=False  # No streaming for now
            )
            
            logger.info(f"DeepSeek response received: {type(response)}, choices: {hasattr(response, 'choices')}")
            if hasattr(response, 'choices'):
                logger.info(f"Choices length: {len(response.choices) if response.choices else 'None'}")
            
            # Log cache hit information if available
            if hasattr(response, 'usage') and response.usage:
                usage = response.usage
                cache_hit_tokens = getattr(usage, 'prompt_cache_hit_tokens', 0)
                cache_miss_tokens = getattr(usage, 'prompt_cache_miss_tokens', 0)
                total_tokens = getattr(usage, 'prompt_tokens', 0)
                
                if cache_hit_tokens > 0:
                    cache_hit_rate = (cache_hit_tokens / total_tokens) * 100 if total_tokens > 0 else 0
                    logger.info(f"DeepSeek cache hit: {cache_hit_tokens}/{total_tokens} tokens ({cache_hit_rate:.1f}%)")
            
            if response and response.choices and len(response.choices) > 0:
                return response.choices[0].message.content
            else:
                logger.error(f"Invalid response from DeepSeek: {response}")
                return "I apologize, but I encountered an error generating a response. Please try again or contact customer service at 1-866-319-8402."
            
        except Exception as e:
            logger.error(f"Error generating response with DeepSeek: {e}")
            logger.error(f"Exception type: {type(e)}")
            logger.error(f"Response object: {response if 'response' in locals() else 'No response variable'}")
            import traceback
            logger.error(f"Full traceback: {traceback.format_exc()}")
            return "I apologize, but I encountered an error generating a response. Please try again or contact customer service at 1-866-319-8402."
    
    def _build_context_string(self, combined_data: Dict[str, Any]) -> str:
        """Build context string from combined data"""
        context_parts = []
        
        # Add primary parts data
        if combined_data["primary_parts"]:
            context_parts.append("=== PARTS FROM DATABASE ===")
            for part in combined_data["primary_parts"][:5]:  # Limit to top 5
                part_info = f"""
Part Number: {part.get('part_number', 'N/A')}
Name: {part.get('name', 'Unknown')}
Price: ${part.get('price', 'N/A')}
Brand: {part.get('brand', 'Unknown')}
Category: {part.get('category', 'Unknown')}
In Stock: {part.get('in_stock', 'Unknown')}
Availability: {part.get('availability', 'Unknown')}
Product URL: {part.get('product_url', 'Not available')}
Installation Video: {part.get('video_url') or part.get('install_video_url', 'Not available')}
Installation Difficulty: {part.get('installation_difficulty', 'Not specified')}
Installation Time: {part.get('installation_time', 'Not specified')}
Description: {(part.get('description') or 'No description')[:200]}...
"""
                context_parts.append(part_info)
        
        # Add repair guides
        if combined_data["primary_repairs"]:
            context_parts.append("\n=== REPAIR GUIDES ===")
            for repair in combined_data["primary_repairs"][:3]:  # Limit to top 3
                repair_info = f"""
Appliance: {repair.get('appliance_type', 'Unknown')}
Symptom: {repair.get('symptom', 'Unknown')}
Description: {(repair.get('description') or 'No description')[:200]}...
Difficulty: {repair.get('difficulty', 'Unknown')}
Parts Needed: {repair.get('parts_needed', 'Not specified')}
Repair Video: {repair.get('repair_video_url', 'Not available')}
Detail URL: {repair.get('symptom_detail_url', 'Not available')}
"""
                context_parts.append(repair_info)
        
        # Add blog articles
        if combined_data["primary_blogs"]:
            context_parts.append("\n=== EDUCATIONAL ARTICLES ===")
            for blog in combined_data["primary_blogs"][:2]:  # Limit to top 2
                blog_info = f"""
Title: {blog.get('title', 'Unknown')}
URL: {blog.get('url', 'Not available')}
Author: {blog.get('author', 'Unknown')}
Excerpt: {blog.get('excerpt', 'No excerpt')[:150]}...
"""
                context_parts.append(blog_info)
        
        # Add vector context if primary data is limited
        if len(combined_data["primary_parts"]) + len(combined_data["primary_repairs"]) < 2:
            if combined_data["additional_parts"]:
                context_parts.append("\n=== ADDITIONAL CONTEXT ===")
                for item in combined_data["additional_parts"][:2]:
                    context_parts.append(f"Additional Info: {item.get('content', '')[:200]}...")
        
        return "\n".join(context_parts) if context_parts else "No relevant data found in database."

class OptimizedRAGOrchestrator:
    """
    Optimized orchestrator using single LLM call approach with conversation memory
    """
    
    def __init__(self):
        self.rag_agent = OptimizedRAGAgent()
        # Import memory manager
        from conversation.memory_manager import get_memory_manager
        self.memory_manager = get_memory_manager()
    
    async def process_query(self, user_query: str, thread_id: str = None) -> Dict[str, Any]:
        """Process a user query with optimized RAG approach and conversation memory"""
        try:
            # Create thread if not exists
            if not thread_id or thread_id not in self.memory_manager.conversations:
                thread_id = self.memory_manager.create_conversation(thread_id)
            
            # Add user query to conversation memory
            self.memory_manager.add_message(thread_id, "user", user_query)
            
            # Get conversation history for RAG agent (excluding current query)
            messages_for_llm = self.memory_manager.get_messages_for_llm(thread_id)
            conversation_history = [msg for msg in messages_for_llm if msg["role"] != "system"][:-1]  # Exclude system and current query
            
            # Process with optimized RAG agent
            result = await self.rag_agent.process_query(
                user_query=user_query,
                conversation_history=conversation_history
            )
            
            if result["success"]:
                # Add assistant response to conversation memory
                self.memory_manager.add_message(thread_id, "assistant", result["response"])
                
                # Get updated conversation history for response
                conversation_history = self.memory_manager.get_conversation_history(thread_id)
                
                # Get conversation stats for debugging
                stats = self.memory_manager.get_conversation_stats(thread_id)
                
                return {
                    "response": result["response"],
                    "thread_id": thread_id,
                    "data_sources": result.get("data_sources", {}),
                    "query_type": result.get("query_type"),
                    "conversation_history": conversation_history,
                    "conversation_stats": stats
                }
            else:
                # Add error response to memory
                self.memory_manager.add_message(thread_id, "assistant", result["response"])
                conversation_history = self.memory_manager.get_conversation_history(thread_id)
                
                return {
                    "response": result["response"],
                    "thread_id": thread_id,
                    "error": result.get("error"),
                    "conversation_history": conversation_history
                }
                
        except Exception as e:
            logger.error(f"Error in optimized RAG orchestrator: {e}")
            error_response = "I apologize, but I encountered an error. Please try again or contact customer service at 1-866-319-8402."
            
            # Add error to memory if thread exists
            if thread_id and thread_id in self.memory_manager.conversations:
                self.memory_manager.add_message(thread_id, "assistant", error_response)
                conversation_history = self.memory_manager.get_conversation_history(thread_id)
            else:
                conversation_history = []
            
            return {
                "response": error_response,
                "thread_id": thread_id,
                "error": str(e),
                "conversation_history": conversation_history
            }
    
    def reset_conversation(self, thread_id: str = None) -> str:
        """Reset conversation to initial state"""
        if thread_id:
            return self.memory_manager.reset_conversation(thread_id)
        else:
            # Create new conversation
            return self.memory_manager.create_conversation()
    
    async def regenerate_last_response(self, thread_id: str) -> Dict[str, Any]:
        """Regenerate the last response"""
        if not thread_id or thread_id not in self.memory_manager.conversations:
            return {
                "response": "No conversation found to regenerate.",
                "thread_id": thread_id,
                "conversation_history": []
            }
        
        # Get last user message before removing
        conversation = self.memory_manager.conversations[thread_id]
        messages = conversation["messages"]
        
        last_user_query = None
        # Find last user message
        for msg in reversed(messages):
            if msg["role"] == "user":
                last_user_query = msg["content"]
                break
        
        if last_user_query:
            # Remove last exchange
            self.memory_manager.remove_last_exchange(thread_id)
            
            # Reprocess the query
            return await self.process_query(last_user_query, thread_id)
        
        return {
            "response": "No previous query to regenerate.",
            "thread_id": thread_id,
            "conversation_history": self.memory_manager.get_conversation_history(thread_id)
        }
    
    def get_conversation_stats(self, thread_id: str) -> Dict[str, Any]:
        """Get conversation statistics"""
        return self.memory_manager.get_conversation_stats(thread_id)
    
    def cleanup_old_conversations(self, max_age_hours: int = 24) -> int:
        """Clean up old conversations"""
        return self.memory_manager.cleanup_old_conversations(max_age_hours)

if __name__ == "__main__":
    import asyncio
    
    async def test_optimized_rag():
        orchestrator = OptimizedRAGOrchestrator()
        
        test_queries = [
            "I need a water filter for my refrigerator",
            "My dishwasher is leaking water",
            "What parts are compatible with model GE GSS25GSHSS?"
        ]
        
        for query in test_queries:
            print(f"\nTesting query: {query}")
            result = await orchestrator.process_query(query)
            print(f"Response: {result['response'][:200]}...")
            print(f"Data sources: {result.get('data_sources', {})}")
            print(f"Query type: {result.get('query_type')}")
    
    asyncio.run(test_optimized_rag())
