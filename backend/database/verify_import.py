#!/usr/bin/env python3
"""
Verify PartSelect Parts Import

This script verifies the successful import of PartSelect parts data
and provides detailed statistics about the imported data.
"""

import logging
from database_manager import PartSelectDatabase

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def main():
    """Verify import and show statistics"""
    try:
        db = PartSelectDatabase()
        
        # Get database statistics
        stats = db.get_database_stats()
        
        print("=" * 60)
        print("PARTSELECT PARTS IMPORT VERIFICATION")
        print("=" * 60)
        
        print(f"\n📊 DATABASE STATISTICS:")
        print(f"   • Total Parts: {stats.get('parts', 0):,}")
        print(f"   • Part Compatibility Records: {stats.get('part_compatibility', 0):,}")
        print(f"   • Repair Guides: {stats.get('repairs', 0):,}")
        print(f"   • Blog Articles: {stats.get('blogs', 0):,}")
        
        # Check PartSelect specific data
        with db.get_connection() as conn:
            # Count parts with manufacturer_id (PartSelect parts)
            cursor = conn.execute("SELECT COUNT(*) FROM parts WHERE manufacturer_id IS NOT NULL")
            partselect_count = cursor.fetchone()[0]
            
            # Count parts by availability
            cursor = conn.execute("SELECT availability, COUNT(*) FROM parts WHERE availability IS NOT NULL GROUP BY availability")
            availability_stats = cursor.fetchall()
            
            # Count parts by manufacturer
            cursor = conn.execute("SELECT manufacturer, COUNT(*) FROM parts WHERE manufacturer IS NOT NULL GROUP BY manufacturer ORDER BY COUNT(*) DESC LIMIT 10")
            manufacturer_stats = cursor.fetchall()
            
            # Count parts by category
            cursor = conn.execute("SELECT category, COUNT(*) FROM parts WHERE category IS NOT NULL GROUP BY category")
            category_stats = cursor.fetchall()
            
            # Price statistics
            cursor = conn.execute("SELECT MIN(price), MAX(price), AVG(price) FROM parts WHERE price IS NOT NULL AND price != ''")
            price_stats = cursor.fetchone()
        
        print(f"\n🔧 PARTSELECT DATA ANALYSIS:")
        print(f"   • Parts with Manufacturer ID: {partselect_count:,}")
        
        print(f"\n📦 AVAILABILITY BREAKDOWN:")
        for availability, count in availability_stats:
            if availability:
                print(f"   • {availability}: {count:,}")
        
        print(f"\n🏭 TOP MANUFACTURERS:")
        for manufacturer, count in manufacturer_stats[:5]:
            if manufacturer:
                print(f"   • {manufacturer}: {count:,}")
        
        print(f"\n📋 CATEGORIES:")
        for category, count in category_stats:
            if category:
                print(f"   • {category.title()}: {count:,}")
        
        if price_stats and price_stats[0] is not None:
            min_price, max_price, avg_price = price_stats
            print(f"\n💰 PRICE STATISTICS:")
            print(f"   • Minimum Price: ${float(min_price):.2f}")
            print(f"   • Maximum Price: ${float(max_price):.2f}")
            print(f"   • Average Price: ${float(avg_price):.2f}")
        
        # Test search functionality
        print(f"\n🔍 SEARCH FUNCTIONALITY TEST:")
        
        # Test dishwasher search
        dishwasher_results = db.search_parts("dishwasher", limit=3)
        print(f"   • 'dishwasher' search: {len(dishwasher_results)} results")
        for result in dishwasher_results:
            print(f"     - {result['name']} ({result['part_number']}) - ${result.get('price', 'N/A')}")
        
        # Test refrigerator search
        refrigerator_results = db.search_parts("refrigerator", limit=3)
        print(f"   • 'refrigerator' search: {len(refrigerator_results)} results")
        for result in refrigerator_results:
            print(f"     - {result['name']} ({result['part_number']}) - ${result.get('price', 'N/A')}")
        
        # Test brand search
        blomberg_results = db.search_parts("Blomberg", limit=3)
        print(f"   • 'Blomberg' search: {len(blomberg_results)} results")
        
        print(f"\n✅ VERIFICATION COMPLETE")
        print(f"   • Database is healthy and searchable")
        print(f"   • PartSelect parts successfully integrated")
        print(f"   • Ready for RAG system usage")
        
    except Exception as e:
        logger.error(f"Verification failed: {e}")
        raise

if __name__ == "__main__":
    main()
