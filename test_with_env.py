#!/usr/bin/env python3
"""
Test the RAG system with proper environment loading
"""

import sys
import asyncio
from pathlib import Path
import os

# Load environment variables from .env file
from dotenv import load_dotenv
load_dotenv()

# Add backend to path
backend_dir = Path(__file__).parent / "backend"
sys.path.append(str(backend_dir))

async def test_with_env():
    """Test the RAG system with environment variables loaded"""
    try:
        print("🔑 API Key Status:")
        deepseek_key = os.getenv("DEEPSEEK_API_KEY")
        voyage_key = os.getenv("VOYAGE_API_KEY")
        
        if deepseek_key:
            print(f"✅ DEEPSEEK_API_KEY is set (starts with: {deepseek_key[:10]}...)")
        else:
            print("❌ DEEPSEEK_API_KEY is not set")
            
        if voyage_key:
            print(f"✅ VOYAGE_API_KEY is set (starts with: {voyage_key[:10]}...)")
        else:
            print("❌ VOYAGE_API_KEY is not set")
        
        if not deepseek_key:
            print("❌ Cannot test without DeepSeek API key")
            return
        
        print("\n🔧 Initializing RAG orchestrator with environment...")
        from agents.optimized_rag_agent import OptimizedRAGOrchestrator
        
        orchestrator = OptimizedRAGOrchestrator()
        print("✅ RAG orchestrator initialized")
        
        print("\n🧪 Testing installation query...")
        result = await orchestrator.process_query(
            user_query="How can I install part number PS11752778?",
            thread_id="test-env"
        )
        
        print(f"\n📊 Result:")
        print(f"Response: {result.get('response', 'No response')}")
        if result.get('error'):
            print(f"Error: {result['error']}")
        else:
            print("✅ No errors!")
        
    except Exception as e:
        print(f"❌ Error testing RAG system: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_with_env())
