#!/usr/bin/env python3
"""
Direct test of the RAG agent to see what's causing the error
"""

import sys
import asyncio
from pathlib import Path

# Add backend to path
backend_dir = Path(__file__).parent / "backend"
sys.path.append(str(backend_dir))

async def test_rag_agent():
    """Test the RAG agent directly"""
    try:
        from agents.optimized_rag_agent import OptimizedRAGOrchestrator
        
        print("🔧 Initializing RAG orchestrator...")
        orchestrator = OptimizedRAGOrchestrator()
        print("✅ RAG orchestrator initialized")
        
        print("\n🧪 Testing installation query...")
        result = await orchestrator.process_query(
            user_query="How can I install part number PS11752778?",
            thread_id="test-direct"
        )
        
        print(f"\n📊 Result:")
        print(f"Response: {result.get('response', 'No response')}")
        print(f"Error: {result.get('error', 'No error')}")
        print(f"Thread ID: {result.get('thread_id', 'No thread ID')}")
        
        if result.get('error'):
            print(f"\n❌ Error details: {result['error']}")
        
    except Exception as e:
        print(f"❌ Error testing RAG agent: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_rag_agent())
