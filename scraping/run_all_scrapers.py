import asyncio
import time
import logging
from datetime import datetime
import os

# Import all our comprehensive scrapers
from comprehensive_parts_scraper import main as scrape_parts
from comprehensive_blog_scraper import main as scrape_blogs  
from comprehensive_repair_scraper import main as scrape_repairs

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('/Users/anujpatel/Study/Projects/InstalilyTask/scraping/data/scraping.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

async def main():
    """Run all comprehensive scrapers in sequence"""
    start_time = datetime.now()
    logger.info("🚀 STARTING COMPREHENSIVE PARTSELECT DATA COLLECTION")
    logger.info(f"⏰ Start time: {start_time}")
    
    # Create data directory if it doesn't exist
    data_dir = '/Users/anujpatel/Study/Projects/InstalilyTask/scraping/data'
    os.makedirs(data_dir, exist_ok=True)
    
    scrapers = [
        {
            'name': 'APPLIANCE PARTS',
            'emoji': '🔧',
            'function': scrape_parts,
            'description': 'Scraping all refrigerator and dishwasher parts from PartSelect'
        },
        {
            'name': 'REPAIR INFORMATION', 
            'emoji': '🛠️',
            'function': scrape_repairs,
            'description': 'Scraping repair symptoms, difficulty levels, and video guides'
        },
        {
            'name': 'BLOG POSTS',
            'emoji': '📚', 
            'function': scrape_blogs,
            'description': 'Scraping all blog posts and articles from PartSelect'
        }
    ]
    
    results = {}
    
    for i, scraper_info in enumerate(scrapers, 1):
        scraper_start = datetime.now()
        logger.info(f"\n{'='*60}")
        logger.info(f"{scraper_info['emoji']} STEP {i}/3: {scraper_info['name']}")
        logger.info(f"📝 {scraper_info['description']}")
        logger.info(f"⏰ Started at: {scraper_start}")
        logger.info(f"{'='*60}\n")
        
        try:
            # Run the scraper
            await scraper_info['function']()
            
            scraper_end = datetime.now()
            scraper_duration = scraper_end - scraper_start
            
            logger.info(f"\n✅ {scraper_info['name']} COMPLETED!")
            logger.info(f"⏱️  Duration: {scraper_duration}")
            
            results[scraper_info['name']] = {
                'status': 'SUCCESS',
                'duration': scraper_duration,
                'start_time': scraper_start,
                'end_time': scraper_end
            }
            
        except Exception as e:
            scraper_end = datetime.now()
            scraper_duration = scraper_end - scraper_start
            
            logger.error(f"\n❌ {scraper_info['name']} FAILED!")
            logger.error(f"💥 Error: {str(e)}")
            logger.error(f"⏱️  Duration before failure: {scraper_duration}")
            
            results[scraper_info['name']] = {
                'status': 'FAILED',
                'error': str(e),
                'duration': scraper_duration,
                'start_time': scraper_start,
                'end_time': scraper_end
            }
        
        # Wait between scrapers to be respectful
        if i < len(scrapers):
            wait_time = 30  # 30 seconds between scrapers
            logger.info(f"\n⏳ Waiting {wait_time} seconds before next scraper...")
            await asyncio.sleep(wait_time)
    
    # Final summary
    end_time = datetime.now()
    total_duration = end_time - start_time
    
    logger.info(f"\n{'='*80}")
    logger.info("🎉 COMPREHENSIVE PARTSELECT DATA COLLECTION COMPLETED!")
    logger.info(f"{'='*80}")
    logger.info(f"⏰ Start time: {start_time}")
    logger.info(f"⏰ End time: {end_time}")
    logger.info(f"⏱️  Total duration: {total_duration}")
    
    # Results summary
    logger.info(f"\n📊 SCRAPING RESULTS SUMMARY:")
    logger.info(f"{'='*40}")
    
    successful = 0
    failed = 0
    
    for scraper_name, result in results.items():
        status_emoji = "✅" if result['status'] == 'SUCCESS' else "❌"
        logger.info(f"{status_emoji} {scraper_name}: {result['status']}")
        logger.info(f"   Duration: {result['duration']}")
        
        if result['status'] == 'SUCCESS':
            successful += 1
        else:
            failed += 1
            logger.info(f"   Error: {result.get('error', 'Unknown error')}")
    
    logger.info(f"\n🎯 FINAL STATS:")
    logger.info(f"   Successful scrapers: {successful}/{len(scrapers)}")
    logger.info(f"   Failed scrapers: {failed}/{len(scrapers)}")
    
    # List generated files
    logger.info(f"\n📁 GENERATED FILES:")
    data_files = []
    for filename in os.listdir(data_dir):
        if filename.endswith(('.json', '.csv')) and not filename.endswith('progress.json'):
            filepath = os.path.join(data_dir, filename)
            file_size = os.path.getsize(filepath)
            data_files.append((filename, file_size))
    
    # Sort files by size (largest first)
    data_files.sort(key=lambda x: x[1], reverse=True)
    
    for filename, size in data_files:
        size_mb = size / (1024 * 1024)
        logger.info(f"   📄 {filename} ({size_mb:.2f} MB)")
    
    total_size = sum([size for _, size in data_files])
    total_size_mb = total_size / (1024 * 1024)
    logger.info(f"\n💾 Total data collected: {total_size_mb:.2f} MB")
    
    if successful == len(scrapers):
        logger.info("\n🏆 ALL SCRAPERS COMPLETED SUCCESSFULLY!")
        logger.info("🎯 Your PartSelect dataset is ready for the AI chat system!")
    else:
        logger.info(f"\n⚠️  {failed} scraper(s) failed. Check logs for details.")
    
    logger.info(f"\n{'='*80}")

if __name__ == "__main__":
    asyncio.run(main())
