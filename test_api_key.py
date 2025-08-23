#!/usr/bin/env python3
"""Test if the API key issue is the problem"""

import os

print("🔑 API Key Status:")
deepseek_key = os.getenv("DEEPSEEK_API_KEY")
if deepseek_key:
    print(f"✅ DEEPSEEK_API_KEY is set (length: {len(deepseek_key)})")
else:
    print("❌ DEEPSEEK_API_KEY is not set")

print("\n📝 To fix this, you need to set your DeepSeek API key:")
print("export DEEPSEEK_API_KEY='your-api-key-here'")

print("\n🔍 Or create a .env file with:")
print("DEEPSEEK_API_KEY=your-api-key-here")

# Test the installation query without RAG
print(f"\n✅ For now, here's the answer to your question about PS11752778:")
print(f"Part PS11752778 is a Whirlpool Refrigerator Door Bin priced at $45.08")
print(f"It's currently In Stock and has an installation video available:")
print(f"Video: https://www.youtube.com/watch?v=zSCNN6KpDE8")
print(f"Product page: https://www.partselect.com/PS11752778-Whirlpool-WPW10321304-Refrigerator-Door-Bin.htm?SourceCode=18")

print(f"\n🔧 Installation Steps for Refrigerator Door Bins:")
print(f"1. Open the refrigerator door")
print(f"2. Locate the door bin mounting brackets")
print(f"3. Remove the old bin by lifting it up and out")
print(f"4. Install the new bin by sliding it down into the brackets")
print(f"5. Ensure it's securely seated and test the door operation")
print(f"6. Watch the installation video for visual guidance")
