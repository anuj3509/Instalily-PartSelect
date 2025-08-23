#!/usr/bin/env python3
"""
Test Part Lookup Script
Tests if a specific part exists and provides installation details
"""

import sys
from database_manager import PartSelectDatabase

def test_part_lookup(part_number):
    """Test looking up a specific part"""
    db = PartSelectDatabase()
    
    print(f"🔍 Looking up part: {part_number}")
    print("=" * 50)
    
    # Try exact match first
    part = db.get_part_by_number(part_number)
    
    if part:
        print("✅ Part found!")
        print(f"  📦 Name: {part['name']}")
        print(f"  💰 Price: ${part.get('price', 'N/A')}")
        print(f"  🏭 Manufacturer: {part.get('manufacturer', 'N/A')}")
        print(f"  🔧 Installation Difficulty: {part.get('installation_difficulty') or 'Not specified'}")
        print(f"  ⏱️  Installation Time: {part.get('installation_time') or 'Not specified'}")
        print(f"  📹 Video URL: {part.get('video_url') or 'Not available'}")
        print(f"  🔗 Product URL: {part.get('product_url', 'N/A')}")
        print(f"  📋 Category: {part.get('category', 'N/A')}")
        print(f"  📦 Availability: {part.get('availability', 'N/A')}")
        
        # Installation guidance
        if part.get('installation_difficulty') or part.get('installation_time'):
            print(f"\n🛠️  Installation Information:")
            if part.get('installation_difficulty'):
                print(f"     Difficulty: {part.get('installation_difficulty')}")
            if part.get('installation_time'):
                print(f"     Time Required: {part.get('installation_time')}")
        
        return True
    else:
        print("❌ Exact part not found")
        
        # Try fuzzy search
        print(f"\n🔍 Searching for similar parts...")
        results = db.search_parts(part_number, limit=5)
        
        if results:
            print(f"Found {len(results)} similar parts:")
            for i, r in enumerate(results, 1):
                print(f"  {i}. {r['part_number']}: {r['name']} - ${r.get('price', 'N/A')}")
        else:
            # Try searching without the PS prefix
            clean_number = part_number.replace('PS', '')
            results = db.search_parts(clean_number, limit=5)
            if results:
                print(f"Found {len(results)} parts with similar numbers:")
                for i, r in enumerate(results, 1):
                    print(f"  {i}. {r['part_number']}: {r['name']} - ${r.get('price', 'N/A')}")
            else:
                print("No similar parts found")
        
        return False

if __name__ == "__main__":
    part_number = sys.argv[1] if len(sys.argv) > 1 else "PS11752778"
    test_part_lookup(part_number)
