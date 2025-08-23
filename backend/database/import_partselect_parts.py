#!/usr/bin/env python3
"""
Import PartSelect Parts Data into Database

This script imports the PartSelect parts data (all_partselect_parts.json) 
into the PartSelect RAG database. It handles the new schema fields and 
ensures data integrity.

Usage:
    python import_partselect_parts.py
"""

import sys
import json
import logging
from pathlib import Path
from database_manager import PartSelectDatabase

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def main():
    """Main import function"""
    try:
        logger.info("Starting PartSelect parts data import...")
        
        # Initialize database
        db = PartSelectDatabase()
        
        # Get initial stats
        initial_stats = db.get_database_stats()
        initial_parts_count = initial_stats.get('parts', 0)
        logger.info(f"Initial parts count: {initial_parts_count}")
        
        # Check if PartSelect parts file exists
        data_dir = Path(__file__).parent.parent.parent / "scraping" / "data"
        partselect_file = data_dir / "all_partselect_parts.json"
        
        if not partselect_file.exists():
            logger.error(f"PartSelect parts file not found: {partselect_file}")
            sys.exit(1)
        
        # Get file info
        with open(partselect_file, 'r') as f:
            parts_data = json.load(f)
        
        logger.info(f"Found {len(parts_data)} parts in PartSelect file")
        
        # Show sample data
        if parts_data:
            sample_part = parts_data[0]
            logger.info("Sample part data:")
            for key, value in sample_part.items():
                logger.info(f"  {key}: {value}")
        
        # Confirm import
        response = input(f"\nProceed with importing {len(parts_data)} PartSelect parts? (y/N): ")
        if response.lower() != 'y':
            logger.info("Import cancelled by user")
            sys.exit(0)
        
        # Import data
        logger.info("Importing PartSelect parts data...")
        db.load_partselect_parts_only()
        
        # Get final stats
        final_stats = db.get_database_stats()
        final_parts_count = final_stats.get('parts', 0)
        parts_added = final_parts_count - initial_parts_count
        
        logger.info(f"Import completed successfully!")
        logger.info(f"Parts added: {parts_added}")
        logger.info(f"Total parts in database: {final_parts_count}")
        
        # Test search functionality
        logger.info("\nTesting search functionality...")
        test_results = db.search_parts("dishwasher", limit=3)
        logger.info(f"Found {len(test_results)} dishwasher parts:")
        for result in test_results:
            logger.info(f"  - {result['name']} ({result['part_number']}) - ${result.get('price', 'N/A')}")
        
        # Show brand distribution
        brands = db.get_brands()
        logger.info(f"\nBrands in database: {len(brands)}")
        logger.info(f"Sample brands: {', '.join(brands[:10])}")
        
        logger.info("\n✅ PartSelect parts import completed successfully!")
        
    except KeyboardInterrupt:
        logger.info("\nImport cancelled by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Error during import: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
