"""
Conversation memory manager for DeepSeek context caching
Maintains chat history for optimal cache utilization
"""

import json
import logging
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
import uuid

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ConversationMemory:
    """
    Manages conversation memory with DeepSeek context caching optimization
    """
    
    def __init__(self):
        # Store conversations by thread_id
        self.conversations: Dict[str, Dict[str, Any]] = {}
        
        # System message that stays consistent for caching
        self.system_message = {
            "role": "system",
            "content": """You are an expert PartSelect AI Assistant specializing in refrigerator and dishwasher parts, repairs, and troubleshooting.

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

**Recommended Parts:**
- [Real part with price and part number]

**Repair Guide:**
[Real repair video URL if available]

**Difficulty:** [Real difficulty rating]

**Next Step:**
[Specific action with real URLs]
```

**CONTENT GUIDELINES:**
- Keep responses 300-600 words based on complexity
- Be thorough but concise
- Always include actionable next steps
- Stay within refrigerator/dishwasher domain
- If no relevant data found, say so honestly

**Out of Scope:**
For other appliances: "I specialize in refrigerator and dishwasher parts and repairs. For [topic], contact PartSelect customer service at 1-866-319-8402."
"""
        }
    
    def create_conversation(self, thread_id: str = None) -> str:
        """Create a new conversation thread"""
        if not thread_id:
            thread_id = str(uuid.uuid4())
        
        # Initialize with welcome message
        welcome_message = """Welcome to PartSelect AI Assistant! I specialize in refrigerator and dishwasher parts and can help you with:

✓ Finding the right appliance parts
✓ Checking part compatibility  
✓ Troubleshooting common issues
✓ Providing repair guidance

What can I help you with today?"""
        
        self.conversations[thread_id] = {
            "thread_id": thread_id,
            "created_at": datetime.now(),
            "last_activity": datetime.now(),
            "messages": [
                self.system_message,
                {"role": "assistant", "content": welcome_message}
            ],
            "message_count": 1
        }
        
        logger.info(f"Created new conversation: {thread_id}")
        return thread_id
    
    def add_message(self, thread_id: str, role: str, content: str) -> bool:
        """Add a message to the conversation"""
        if thread_id not in self.conversations:
            logger.warning(f"Thread {thread_id} not found, creating new conversation")
            self.create_conversation(thread_id)
        
        conversation = self.conversations[thread_id]
        
        # Add message
        conversation["messages"].append({
            "role": role,
            "content": content
        })
        
        # Update metadata
        conversation["last_activity"] = datetime.now()
        if role == "user":
            conversation["message_count"] += 1
        
        logger.info(f"Added {role} message to thread {thread_id} (total messages: {len(conversation['messages'])})")
        return True
    
    def get_messages_for_llm(self, thread_id: str, include_system: bool = True) -> List[Dict[str, str]]:
        """
        Get messages formatted for DeepSeek API with optimal caching
        The system message + conversation history will be cached by DeepSeek
        """
        if thread_id not in self.conversations:
            logger.warning(f"Thread {thread_id} not found")
            return [self.system_message] if include_system else []
        
        conversation = self.conversations[thread_id]
        messages = conversation["messages"].copy()
        
        if not include_system:
            # Remove system message if requested
            messages = [msg for msg in messages if msg["role"] != "system"]
        
        return messages
    
    def get_conversation_history(self, thread_id: str) -> List[Dict[str, str]]:
        """Get conversation history excluding system message"""
        if thread_id not in self.conversations:
            return []
        
        conversation = self.conversations[thread_id]
        # Return all messages except system message
        return [msg for msg in conversation["messages"] if msg["role"] != "system"]
    
    def reset_conversation(self, thread_id: str) -> str:
        """Reset conversation to initial state"""
        if thread_id in self.conversations:
            del self.conversations[thread_id]
        
        return self.create_conversation(thread_id)
    
    def remove_last_exchange(self, thread_id: str) -> bool:
        """Remove last user query and assistant response for regeneration"""
        if thread_id not in self.conversations:
            return False
        
        conversation = self.conversations[thread_id]
        messages = conversation["messages"]
        
        # Remove last assistant message if present
        if messages and messages[-1]["role"] == "assistant":
            messages.pop()
        
        # Remove last user message if present
        if messages and messages[-1]["role"] == "user":
            messages.pop()
            conversation["message_count"] = max(0, conversation["message_count"] - 1)
        
        logger.info(f"Removed last exchange from thread {thread_id}")
        return True
    
    def get_conversation_stats(self, thread_id: str) -> Dict[str, Any]:
        """Get conversation statistics"""
        if thread_id not in self.conversations:
            return {}
        
        conversation = self.conversations[thread_id]
        messages = conversation["messages"]
        
        user_messages = sum(1 for msg in messages if msg["role"] == "user")
        assistant_messages = sum(1 for msg in messages if msg["role"] == "assistant")
        
        # Calculate potential cache efficiency
        total_tokens_estimate = sum(len(msg["content"].split()) * 1.3 for msg in messages)  # Rough token estimate
        
        return {
            "thread_id": thread_id,
            "created_at": conversation["created_at"],
            "last_activity": conversation["last_activity"],
            "total_messages": len(messages),
            "user_messages": user_messages,
            "assistant_messages": assistant_messages,
            "estimated_tokens": int(total_tokens_estimate),
            "cache_efficiency": "High" if len(messages) > 4 else "Medium" if len(messages) > 2 else "Low"
        }
    
    def cleanup_old_conversations(self, max_age_hours: int = 24):
        """Clean up old conversations to save memory"""
        cutoff_time = datetime.now() - timedelta(hours=max_age_hours)
        
        threads_to_remove = []
        for thread_id, conversation in self.conversations.items():
            if conversation["last_activity"] < cutoff_time:
                threads_to_remove.append(thread_id)
        
        for thread_id in threads_to_remove:
            del self.conversations[thread_id]
            logger.info(f"Cleaned up old conversation: {thread_id}")
        
        return len(threads_to_remove)
    
    def get_all_conversations(self) -> Dict[str, Dict[str, Any]]:
        """Get summary of all active conversations"""
        summary = {}
        for thread_id, conversation in self.conversations.items():
            summary[thread_id] = {
                "created_at": conversation["created_at"],
                "last_activity": conversation["last_activity"],
                "message_count": conversation["message_count"],
                "total_messages": len(conversation["messages"])
            }
        return summary

# Global memory manager instance
memory_manager = ConversationMemory()

def get_memory_manager() -> ConversationMemory:
    """Get the global memory manager instance"""
    return memory_manager

if __name__ == "__main__":
    # Test the memory manager
    manager = ConversationMemory()
    
    # Create conversation
    thread_id = manager.create_conversation()
    print(f"Created thread: {thread_id}")
    
    # Add messages
    manager.add_message(thread_id, "user", "I need a water filter")
    manager.add_message(thread_id, "assistant", "I can help you find water filters...")
    
    # Get messages for LLM
    messages = manager.get_messages_for_llm(thread_id)
    print(f"Messages for LLM: {len(messages)}")
    
    # Get stats
    stats = manager.get_conversation_stats(thread_id)
    print(f"Conversation stats: {stats}")
