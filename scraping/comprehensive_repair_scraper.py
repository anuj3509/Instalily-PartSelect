import asyncio
import json
import csv
import time
import random
from playwright.async_api import async_playwright
from dataclasses import dataclass, asdict
from typing import List, Dict, Optional, Set
import re
import logging
from urllib.parse import urljoin, urlparse

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

@dataclass
class RepairInfo:
    product: str
    symptom: str
    description: str
    percentage: str
    parts: str
    symptom_detail_url: str
    difficulty: str
    repair_video_url: str

class ComprehensiveRepairScraper:
    def __init__(self):
        self.base_url = "https://www.partselect.com"
        self.visited_urls: Set[str] = set()
    
    async def create_stealth_context(self, playwright):
        """Create a stealth browser context"""
        browser = await playwright.chromium.launch(
            headless=False,
            args=[
                '--disable-blink-features=AutomationControlled',
                '--disable-infobars',
                '--disable-extensions',
                '--no-sandbox',
                '--disable-dev-shm-usage',
                '--disable-gpu',
                '--window-size=1920,1080',
            ]
        )
        
        context = await browser.new_context(
            user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
            viewport={'width': 1920, 'height': 1080},
            locale='en-US',
            timezone_id='America/New_York',
            extra_http_headers={
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.5',
                'Accept-Encoding': 'gzip, deflate, br',
                'DNT': '1',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1',
            }
        )
        
        await context.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined,
            });
            
            Object.defineProperty(window, 'chrome', {
                writable: true,
                enumerable: true,
                configurable: false,
                value: { runtime: {} },
            });
        """)
        
        return browser, context
    
    async def human_like_navigation(self, page, url):
        """Navigate with human-like behavior"""
        logger.info(f"🌐 Navigating to: {url}")
        
        await asyncio.sleep(random.uniform(2, 4))
        
        try:
            await page.goto(url, wait_until='domcontentloaded', timeout=45000)
            await page.wait_for_timeout(random.randint(2000, 4000))
            
            # Scroll to simulate reading
            await page.evaluate('window.scrollTo(0, document.body.scrollHeight/3)')
            await page.wait_for_timeout(random.randint(1000, 2000))
            
            return True
        except Exception as e:
            logger.error(f"❌ Navigation failed: {e}")
            return False
    
    async def extract_symptom_data(self, symptom_element):
        """Extract data from a symptom element"""
        try:
            # Get the URL
            url = await symptom_element.get_attribute("href")
            if not url:
                return None
            
            # Get the symptom name
            title_element = await symptom_element.query_selector('.title-md')
            if not title_element:
                return None
            symptom = await title_element.text_content()
            symptom = symptom.strip() if symptom else ""
            
            # Get the description
            description_element = await symptom_element.query_selector('p')
            description = ""
            if description_element:
                description = await description_element.text_content()
                description = description.strip() if description else ""
            
            # Get the percentage
            percentage = "0"
            percentage_element = await symptom_element.query_selector('.symptom-list__reported-by')
            if percentage_element:
                percentage_text = await percentage_element.text_content()
                if percentage_text:
                    percentage = percentage_text.split("%")[0].strip()
            
            return {
                'symptom': symptom,
                'description': description,
                'percentage': percentage,
                'symptom_detail_url': url
            }
            
        except Exception as e:
            logger.error(f"❌ Error extracting symptom data: {e}")
            return None
    
    async def get_repair_details(self, page, url):
        """Get repair details from a symptom page"""
        try:
            if not await self.human_like_navigation(page, url):
                return {'parts': '', 'difficulty': '', 'repair_video_url': ''}
            
            # Wait for repair intro section
            try:
                await page.wait_for_selector('.repair__intro', timeout=10000)
            except:
                logger.warning("⚠️ Repair intro section not found")
            
            # Get difficulty
            difficulty = ""
            try:
                difficulty_selectors = ['ul.list-disc li', '.difficulty', '.repair-difficulty']
                for selector in difficulty_selectors:
                    element = await page.query_selector(selector)
                    if element:
                        difficulty_text = await element.text_content()
                        if difficulty_text and 'rated as' in difficulty_text.lower():
                            difficulty = difficulty_text.replace("Rated as", "").strip()
                            break
            except:
                pass
            
            # Get parts
            parts = []
            try:
                part_selectors = [
                    'div.repair__intro a.js-scrollTrigger',
                    '.parts-list a',
                    '.repair-parts a'
                ]
                
                for selector in part_selectors:
                    elements = await page.query_selector_all(selector)
                    if elements:
                        for link in elements:
                            part_name = await link.text_content()
                            if part_name and part_name.strip():
                                parts.append(part_name.strip())
                        break
            except:
                pass
            
            # Get video URL
            video_url = ""
            try:
                video_selectors = [
                    'div[data-yt-init]',
                    '.video-container[data-yt-init]',
                    '.youtube-video[data-yt-init]'
                ]
                
                for selector in video_selectors:
                    element = await page.query_selector(selector)
                    if element:
                        video_id = await element.get_attribute("data-yt-init")
                        if video_id:
                            video_url = f"https://www.youtube.com/watch?v={video_id}"
                            logger.info(f"🎥 Found video URL: {video_url}")
                            break
            except:
                pass
            
            return {
                'parts': ", ".join(parts),
                'difficulty': difficulty,
                'repair_video_url': video_url
            }
            
        except Exception as e:
            logger.error(f"❌ Error getting repair details: {e}")
            return {'parts': '', 'difficulty': '', 'repair_video_url': ''}
    
    async def scrape_appliance_repairs(self, appliance_type, base_url):
        """Scrape repair information for a specific appliance type"""
        repairs = []
        
        async with async_playwright() as p:
            browser, context = await self.create_stealth_context(p)
            page = await context.new_page()
            
            try:
                logger.info(f"🔧 Starting {appliance_type} repair scraping...")
                
                if not await self.human_like_navigation(page, base_url):
                    logger.error(f"❌ Failed to load {appliance_type} base URL")
                    return repairs
                
                # Wait for symptom list
                try:
                    await page.wait_for_selector('.symptom-list', timeout=30000)
                    logger.info("✅ Found symptom list")
                except:
                    logger.error("❌ Symptom list not found")
                    return repairs
                
                # Get all symptom elements
                symptom_elements = await page.query_selector_all('.symptom-list a')
                logger.info(f"🔍 Found {len(symptom_elements)} symptoms")
                
                # Extract initial symptom data
                symptom_data_list = []
                for idx, element in enumerate(symptom_elements, 1):
                    logger.info(f"📋 Collecting initial data for symptom {idx}/{len(symptom_elements)}")
                    
                    symptom_data = await self.extract_symptom_data(element)
                    if symptom_data:
                        symptom_data_list.append(symptom_data)
                        logger.info(f"✅ Collected: {symptom_data['symptom']}")
                
                logger.info(f"📊 Processing {len(symptom_data_list)} collected symptoms")
                
                # Process each symptom
                for idx, symptom_data in enumerate(symptom_data_list, 1):
                    logger.info(f"🔧 Processing symptom {idx}/{len(symptom_data_list)}: {symptom_data['symptom']}")
                    
                    # Get repair details
                    full_url = urljoin(base_url, symptom_data['symptom_detail_url'])
                    repair_details = await self.get_repair_details(page, full_url)
                    
                    # Combine all data
                    repair_entry = RepairInfo(
                        product=appliance_type,
                        symptom=symptom_data['symptom'],
                        description=symptom_data['description'],
                        percentage=symptom_data['percentage'],
                        parts=repair_details['parts'],
                        symptom_detail_url=full_url,
                        difficulty=repair_details['difficulty'],
                        repair_video_url=repair_details['repair_video_url']
                    )
                    
                    repairs.append(repair_entry)
                    
                    logger.info(f"✅ Processed: {repair_entry.symptom}")
                    if repair_entry.parts:
                        logger.info(f"🔧 Parts: {repair_entry.parts}")
                    if repair_entry.difficulty:
                        logger.info(f"📊 Difficulty: {repair_entry.difficulty}")
                    if repair_entry.repair_video_url:
                        logger.info(f"🎥 Video: {repair_entry.repair_video_url}")
                    
                    # Delay between symptom processing
                    await asyncio.sleep(random.uniform(3, 5))
                
            finally:
                await browser.close()
        
        return repairs
    
    def save_to_json(self, repairs: List[RepairInfo], filename: str):
        """Save repairs to JSON file"""
        data = [asdict(repair) for repair in repairs]
        
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        
        logger.info(f"💾 Saved {len(repairs)} repairs to {filename}")
    
    def save_to_csv(self, repairs: List[RepairInfo], filename: str):
        """Save repairs to CSV file"""
        if not repairs:
            logger.warning("No repairs to save")
            return
            
        fieldnames = ['product', 'symptom', 'description', 'percentage', 'parts', 
                     'symptom_detail_url', 'difficulty', 'repair_video_url']
        
        with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows([asdict(repair) for repair in repairs])
        
        logger.info(f"💾 Saved {len(repairs)} repairs to {filename}")

async def main():
    """Main repair scraping function"""
    scraper = ComprehensiveRepairScraper()
    
    appliances = [
        {
            'type': 'Dishwasher',
            'url': 'https://www.partselect.com/Repair/Dishwasher/',
        },
        {
            'type': 'Refrigerator',
            'url': 'https://www.partselect.com/Repair/Refrigerator/',
        }
    ]
    
    all_repairs = []
    
    for appliance in appliances:
        appliance_type = appliance['type']
        appliance_url = appliance['url']
        
        logger.info(f"🔧 Starting {appliance_type.upper()} repair scraping...")
        repairs = await scraper.scrape_appliance_repairs(appliance_type, appliance_url)
        
        all_repairs.extend(repairs)
        
        # Save appliance-specific files
        if repairs:
            scraper.save_to_json(repairs, f'/Users/anujpatel/Study/Projects/InstalilyTask/scraping/data/{appliance_type.lower()}_repairs.json')
            scraper.save_to_csv(repairs, f'/Users/anujpatel/Study/Projects/InstalilyTask/scraping/data/{appliance_type.lower()}_repairs.csv')
        
        logger.info(f"✅ {appliance_type.upper()} repair scraping completed: {len(repairs)} repairs")
        
        # Delay between appliances
        if appliance != appliances[-1]:
            delay = random.uniform(10, 15)
            logger.info(f"⏳ Waiting {delay:.1f} seconds before next appliance...")
            await asyncio.sleep(delay)
    
    # Save combined data
    if all_repairs:
        scraper.save_to_json(all_repairs, '/Users/anujpatel/Study/Projects/InstalilyTask/scraping/data/all_repairs.json')
        scraper.save_to_csv(all_repairs, '/Users/anujpatel/Study/Projects/InstalilyTask/scraping/data/all_repairs.csv')
    
    logger.info(f"🎉 COMPREHENSIVE REPAIR SCRAPING COMPLETED!")
    logger.info(f"🔧 Total repairs scraped: {len(all_repairs)}")
    
    # Summary by appliance
    dishwasher_count = len([r for r in all_repairs if r.product == 'Dishwasher'])
    refrigerator_count = len([r for r in all_repairs if r.product == 'Refrigerator'])
    
    logger.info(f"🍽️  Dishwasher repairs: {dishwasher_count}")
    logger.info(f"🧊 Refrigerator repairs: {refrigerator_count}")

if __name__ == "__main__":
    asyncio.run(main())
