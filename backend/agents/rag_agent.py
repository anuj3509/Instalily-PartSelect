"""
RAG-based agent that uses tool calling to access real data
This agent replaces the old workflow with a more agentic approach
"""

import json
import logging
from typing import Dict, List, Any, Optional
from openai import AsyncOpenAI
import instructor
from pathlib import Path
from dotenv import load_dotenv
import os

# Load environment variables
current_dir = Path(__file__).parent
project_root = current_dir.parent.parent
env_path = project_root / '.env'
load_dotenv(env_path)

from tools.database_tools import AVAILABLE_TOOLS

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class RAGAssistantAgent:
    """
    RAG-based assistant that uses tool calling to access real PartSelect data.
    This agent directly handles user queries and makes tool calls as needed.
    """
    
    def __init__(self):
        # Initialize OpenAI client with instructor
        openai_client = AsyncOpenAI(
            api_key=os.getenv("DEEPSEEK_API_KEY"),
            base_url="https://api.deepseek.com"
        )
        self.client = instructor.patch(openai_client)
        
        # System prompt for the RAG assistant
        self.system_prompt = """You are an expert PartSelect AI Assistant specializing in refrigerator and dishwasher parts, repairs, and troubleshooting.

**CORE CAPABILITIES:**
- Finding the right appliance parts with real product information
- Checking part compatibility with specific appliance models  
- Providing step-by-step troubleshooting guidance
- Recommending repair procedures with video guides

**TOOL USAGE GUIDELINES:**
You have access to several database tools that provide REAL PartSelect data:

1. **search_parts** - Search for parts by name, description, or function
   - Use for: "I need a water filter", "door seal for refrigerator"
   - Always check real inventory and prices

2. **get_part_details** - Get detailed info about a specific part number
   - Use when user mentions a specific part number (PS123, W10234, etc.)
   - Use for part installation questions, specifications, pricing, availability
   - Provides real URLs, specifications, installation guides, and video links
   - This is the PRIMARY tool for part-specific queries

3. **search_compatible_parts** - Find parts for specific appliance models
   - Use when user provides model number
   - Returns actual compatibility data

4. **search_repair_guides** - Find troubleshooting guides for symptoms
   - Use for: "dishwasher is leaking", "refrigerator not cooling"
   - Provides real repair videos and difficulty ratings

5. **search_blog_content** - Find educational articles
   - Use for general maintenance, tips, or detailed explanations

**RESPONSE GUIDELINES:**

**ALWAYS use tools** when the user asks about:
- Specific parts or part searches
- Model compatibility 
- Repair procedures or troubleshooting
- Prices, availability, or specifications

**URL HANDLING:**
- ONLY provide URLs returned by the database tools
- NEVER generate or guess URLs
- If no real URL is available, don't mention URLs
- Always use real product_url, repair_video_url, or blog URLs from tools

**FORMATTING GUIDELINES:**
- Use proper markdown formatting with `- ` for bullet points
- Add blank lines before **Next Step:** sections
- Structure responses with clear headers
- Keep responses concise but thorough (300-600 words based on complexity)
- Always include real prices when available
- Provide part numbers for easy ordering

**RESPONSE STRUCTURE:**
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

**Installation Video:**
[Include YouTube video link if available]

**Installation:**
[Real installation guidance if available]

**Next Step:**
[Order link or compatibility check suggestion]
```

For **Troubleshooting** queries:
```
## [Symptom] - [Appliance Type]

**Most Likely Causes:**
- [Real cause from database]
- [Real cause from database]

**Recommended Parts:**
- [Real part with price and part number]
- [Real part with price and part number]

**Repair Guide:**
[Link to real repair video if available]

**Difficulty:** [Real difficulty rating]

**Next Step:**
[Specific action with real URLs]
```

For **Compatibility** queries:
```
## Compatible Parts for Model [Model Number]

**Found [X] Compatible Parts:**
- [Real part name] ([Part number]) - $[Price]
- [Real part name] ([Part number]) - $[Price]

**Installation Resources:**
[Real video links or guides if available]

**Next Step:**
[Order information with real URLs]
```

**IMPORTANT RULES:**
1. **Always call tools first** before responding to part/repair queries
2. **For specific part numbers (PS123, W10234, etc.), ALWAYS use get_part_details tool first**
3. **Use ONLY real data** from tool responses
4. **Never generate fake URLs, prices, or part numbers**
5. **Stay within refrigerator/dishwasher domain**
6. **Be helpful but accurate** - if tools return no results, say so
7. **Provide actionable next steps** with real links when available
8. **CRITICAL: After tool execution, generate ONLY clean, human-readable text - NEVER include tool call syntax, tokens, or internal formatting**
9. **CRITICAL: Your final response must be natural language that a customer can read and understand**

**Out of Scope Responses:**
If asked about other appliances or non-repair topics, politely redirect:
"I specialize in refrigerator and dishwasher parts and repairs. For [topic], I'd recommend contacting PartSelect customer service at 1-866-319-8402."

Remember: You're representing PartSelect, so maintain professionalism and accuracy. Always use real data from the tools rather than making assumptions."""

    async def process_query(self, user_query: str, conversation_history: List[Dict[str, str]] = None) -> Dict[str, Any]:
        """
        Process a user query using RAG approach with tool calling
        """
        try:
            # Build conversation context
            messages = [{"role": "system", "content": self.system_prompt}]
            
            # Add conversation history if provided - ensure all messages are serializable
            if conversation_history:
                for msg in conversation_history:
                    if isinstance(msg, dict) and "role" in msg and "content" in msg:
                        # Ensure content is a string
                        content = str(msg.get("content", ""))
                        messages.append({
                            "role": msg["role"],
                            "content": content
                        })
                    else:
                        logger.warning(f"Skipping non-serializable message: {type(msg)}")
            
            # Add current user query
            messages.append({"role": "user", "content": str(user_query)})
            
            # Validate all messages are serializable
            for i, msg in enumerate(messages):
                if not isinstance(msg, dict) or "role" not in msg or "content" not in msg:
                    logger.error(f"Invalid message format at index {i}: {msg}")
                    raise ValueError(f"Invalid message format: {msg}")
                if not isinstance(msg["content"], str):
                    msg["content"] = str(msg["content"])
            
            # Create tools for OpenAI function calling
            tools = self._create_openai_tools()
            
            # Log the messages being sent to LLM
            try:
                logger.info(f"🔍 Sending to LLM - Messages: {json.dumps(messages, indent=2)}")
            except:
                logger.info(f"🔍 Sending to LLM - Messages count: {len(messages)}")
            logger.info(f"🔧 Available tools: {[tool['function']['name'] for tool in tools]}")
            
            # Make initial request with tools
            response = await self.client.chat.completions.create(
                model="deepseek-chat",
                messages=messages,
                tools=tools,
                tool_choice="auto",  # Let the model decide when to use tools
                temperature=0.1,  # Lower temperature for more consistent responses
                max_tokens=2000
            )
            
            # Log the LLM response
            logger.info(f"🤖 LLM Response: {response.choices[0].message.content}")
            if response.choices[0].message.tool_calls:
                logger.info(f"🔧 Tool calls requested: {[tc.function.name for tc in response.choices[0].message.tool_calls]}")
            
            # Handle tool calls
            if response.choices[0].message.tool_calls:
                # Execute tool calls - extract only serializable content
                assistant_message = {
                    "role": "assistant",
                    "content": response.choices[0].message.content or "",
                    "tool_calls": [
                        {
                            "id": tc.id,
                            "type": "function",
                            "function": {
                                "name": tc.function.name,
                                "arguments": tc.function.arguments
                            }
                        }
                        for tc in response.choices[0].message.tool_calls
                    ]
                }
                messages.append(assistant_message)
                
                for tool_call in response.choices[0].message.tool_calls:
                    tool_name = tool_call.function.name
                    tool_args = json.loads(tool_call.function.arguments)
                    
                    logger.info(f"Executing tool: {tool_name} with args: {tool_args}")
                    
                    # Execute the tool
                    if tool_name in AVAILABLE_TOOLS:
                        tool_function = AVAILABLE_TOOLS[tool_name]["function"]
                        logger.info(f"🔧 Executing tool {tool_name} with args: {tool_args}")
                        tool_result = tool_function(**tool_args)
                        logger.info(f"🔧 Tool {tool_name} result: {tool_result[:500]}...")
                        
                        # Add tool result to conversation - ensure it's a string
                        tool_content = str(tool_result) if tool_result else ""
                        messages.append({
                            "role": "tool",
                            "tool_call_id": tool_call.id,
                            "content": tool_content
                        })
                
                # Log messages before final response
                try:
                    logger.info(f"🔍 Messages before final response: {json.dumps(messages, indent=2)}")
                except:
                    logger.info(f"🔍 Messages before final response count: {len(messages)}")
                
                # Add instruction for clean response generation
                messages.append({
                    "role": "user",
                    "content": "Now generate a clean, human-readable response based on the tool results. DO NOT include any tool call syntax, tokens, or internal formatting. Write as if you're speaking directly to a customer."
                })
                
                # Get final response after tool execution
                final_response = await self.client.chat.completions.create(
                    model="deepseek-chat",
                    messages=messages,
                    temperature=0.1,
                    max_tokens=2000
                )
                
                final_content = final_response.choices[0].message.content
                
                # Clean up any remaining tokens or internal formatting
                if final_content:
                    # Remove any tool call syntax or tokens
                    final_content = final_content.replace("REDACTED_SPECIAL_TOKEN", "")
                    final_content = final_content.replace("<|tool_calls_begin|>", "")
                    final_content = final_content.replace("<|tool_calls_end|>", "")
                    final_content = final_content.replace("<|tool_call_begin|>", "")
                    final_content = final_content.replace("<|tool_call_end|>", "")
                    final_content = final_content.replace("<|tool_sep|>", "")
                    
                    # Clean up any remaining formatting artifacts
                    final_content = final_content.strip()
                    
                    # If content is empty after cleaning, provide a fallback
                    if not final_content or len(final_content.strip()) < 10:
                        final_content = "I apologize, but I encountered an issue generating the response. Please try asking your question again."
                
                logger.info(f"🤖 Final LLM Response (cleaned): {final_content}")
            else:
                # No tools needed, use direct response
                direct_content = response.choices[0].message.content
                
                # Clean up any tokens or internal formatting
                if direct_content:
                    direct_content = direct_content.replace("REDACTED_SPECIAL_TOKEN", "")
                    direct_content = direct_content.replace("<|tool_calls_begin|>", "")
                    direct_content = direct_content.replace("<|tool_calls_end|>", "")
                    direct_content = direct_content.replace("<|tool_call_begin|>", "")
                    direct_content = direct_content.replace("<|tool_call_end|>", "")
                    direct_content = direct_content.replace("<|tool_sep|>", "")
                    direct_content = direct_content.strip()
                
                logger.info(f"🤖 No tools needed, direct response (cleaned): {direct_content}")
                final_content = direct_content
            
            logger.info(f"✅ Returning final response: {final_content[:200]}...")
            
            # Ensure tools_used is properly extracted
            tools_used = []
            if response.choices[0].message.tool_calls:
                tools_used = [tc.function.name for tc in response.choices[0].message.tool_calls]
            
            return {
                "success": True,
                "response": final_content,
                "tools_used": tools_used,
                "message": "Query processed successfully"
            }
            
        except Exception as e:
            import traceback
            logger.error(f"Error processing query: {e}")
            logger.error(f"Full traceback: {traceback.format_exc()}")
            return {
                "success": False,
                "response": "I apologize, but I encountered an error processing your request. Please try again or contact customer service at 1-866-319-8402.",
                "error": str(e),
                "message": "Failed to process query"
            }
    
    def _create_openai_tools(self) -> List[Dict[str, Any]]:
        """Convert our tools to OpenAI function calling format"""
        openai_tools = []
        
        for tool_name, tool_info in AVAILABLE_TOOLS.items():
            openai_tool = {
                "type": "function",
                "function": {
                    "name": tool_name,
                    "description": tool_info["description"],
                    "parameters": tool_info["parameters"]
                }
            }
            openai_tools.append(openai_tool)
        
        return openai_tools

class RAGOrchestrator:
    """
    Simple orchestrator that uses the RAG agent directly
    This replaces the complex LangGraph workflow with a simpler, more agentic approach
    """
    
    def __init__(self):
        self.rag_agent = RAGAssistantAgent()
        self.conversation_history: List[Dict[str, str]] = [
            {
                "role": "assistant", 
                "content": self._get_introduction_message()
            }
        ]
    
    def _get_introduction_message(self) -> str:
        """Get the standard welcome message"""
        return """Welcome to PartSelect AI Assistant! I specialize in refrigerator and dishwasher parts and can help you with:

✓ Finding the right appliance parts
✓ Checking part compatibility  
✓ Troubleshooting common issues
✓ Providing repair guidance

What can I help you with today?"""
    
    async def process_query(self, user_query: str, thread_id: str = None) -> Dict[str, Any]:
        """Process a user query and maintain conversation history"""
        try:
            # Add user query to history
            self.conversation_history.append({
                "role": "user",
                "content": user_query
            })
            
            # Process with RAG agent
            result = await self.rag_agent.process_query(
                user_query=user_query,
                conversation_history=self.conversation_history[:-1]  # Exclude the current query
            )
            
            if result["success"]:
                # Add assistant response to history
                self.conversation_history.append({
                    "role": "assistant",
                    "content": result["response"]
                })
                
                return {
                    "response": result["response"],
                    "tools_used": result.get("tools_used", []),
                    "conversation_history": self.conversation_history
                }
            else:
                return {
                    "response": result["response"],
                    "error": result.get("error"),
                    "conversation_history": self.conversation_history
                }
                
        except Exception as e:
            logger.error(f"Error in RAG orchestrator: {e}")
            error_response = "I apologize, but I encountered an error. Please try again or contact customer service at 1-866-319-8402."
            
            self.conversation_history.append({
                "role": "assistant",
                "content": error_response
            })
            
            return {
                "response": error_response,
                "error": str(e),
                "conversation_history": self.conversation_history
            }
    
    def reset_conversation(self):
        """Reset conversation history"""
        self.conversation_history = [
            {
                "role": "assistant", 
                "content": self._get_introduction_message()
            }
        ]
    
    async def regenerate_last_response(self) -> Dict[str, Any]:
        """Regenerate the last response"""
        if len(self.conversation_history) >= 2:
            # Remove last assistant response
            last_user_query = None
            if self.conversation_history[-2]["role"] == "user":
                last_user_query = self.conversation_history[-2]["content"]
                # Remove both user query and assistant response
                self.conversation_history = self.conversation_history[:-2]
            
            if last_user_query:
                # Reprocess the query
                return await self.process_query(last_user_query)
        
        return {
            "response": "No previous query to regenerate.",
            "conversation_history": self.conversation_history
        }

# Test the RAG agent
if __name__ == "__main__":
    import asyncio
    
    async def test_rag_agent():
        orchestrator = RAGOrchestrator()
        
        test_queries = [
            "I need a water filter for my refrigerator",
            "My dishwasher is leaking water",
            "What parts are compatible with model GE GSS25GSHSS?"
        ]
        
        for query in test_queries:
            print(f"\nTesting query: {query}")
            result = await orchestrator.process_query(query)
            print(f"Response: {result['response'][:200]}...")
            print(f"Tools used: {result.get('tools_used', [])}")
    
    asyncio.run(test_rag_agent())
