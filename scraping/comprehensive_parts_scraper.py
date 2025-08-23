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
class Product:
    part_number: str
    name: str
    description: str
    price: float
    brand: str
    category: str
    image_url: str
    product_url: str
    compatibility_models: List[str]
    installation_guide: str
    specifications: Dict[str, str]
    in_stock: bool

class ComprehensivePartsScraper:
    def __init__(self):
        self.base_url = "https://www.partselect.com"
        self.products = []
        self.visited_urls: Set[str] = set()
    
    async def create_stealth_context(self, playwright):
        """Create a stealth browser context that mimics real user behavior"""
        browser = await playwright.chromium.launch(
            headless=False,  # Run in visible mode initially to see what's happening
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
        
        # Create context with realistic settings
        context = await browser.new_context(
            user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
            viewport={'width': 1920, 'height': 1080},
            locale='en-US',
            timezone_id='America/New_York',
            geolocation={'latitude': 40.7128, 'longitude': -74.0060},
            permissions=['geolocation'],
            extra_http_headers={
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.5',
                'Accept-Encoding': 'gzip, deflate, br',
                'DNT': '1',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1',
            }
        )
        
        # Add stealth script
        await context.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined,
            });
            
            Object.defineProperty(window, 'chrome', {
                writable: true,
                enumerable: true,
                configurable: false,
                value: {
                    runtime: {},
                },
            });
            
            Object.defineProperty(navigator, 'plugins', {
                get: () => [1, 2, 3, 4, 5],
            });
            
            Object.defineProperty(navigator, 'languages', {
                get: () => ['en-US', 'en'],
            });
        """)
        
        return browser, context
    
    async def human_like_navigation(self, page, url):
        """Navigate to URL with human-like behavior"""
        logger.info(f"🌐 Navigating to: {url}")
        
        # Random delay before navigation
        await asyncio.sleep(random.uniform(2, 4))
        
        try:
            # Navigate with realistic timeout
            await page.goto(url, wait_until='domcontentloaded', timeout=45000)
            
            # Wait for page to settle
            await page.wait_for_timeout(random.randint(2000, 4000))
            
            # Simulate human scrolling
            await page.evaluate('window.scrollTo(0, document.body.scrollHeight/4)')
            await page.wait_for_timeout(random.randint(1000, 2000))
            
            await page.evaluate('window.scrollTo(0, document.body.scrollHeight/2)')
            await page.wait_for_timeout(random.randint(1000, 2000))
            
            return True
        except Exception as e:
            logger.error(f"❌ Navigation failed: {e}")
            return False
    
    async def discover_category_links(self, page, category_url):
        """Discover all product and subcategory links from main category page"""
        links = set()
        
        if not await self.human_like_navigation(page, category_url):
            return links
        
        try:
            # Wait for navigation links to load
            await page.wait_for_selector('.nf__links', timeout=10000)
            
            # Get all brand/subcategory links
            brand_links = await page.query_selector_all('.nf__links a')
            
            for link in brand_links:
                href = await link.get_attribute('href')
                if href:
                    full_url = urljoin(self.base_url, href)
                    links.add(full_url)
                    logger.info(f"📂 Found category link: {full_url}")
            
            logger.info(f"✅ Discovered {len(links)} category links")
            
        except Exception as e:
            logger.error(f"❌ Error discovering links: {e}")
        
        return links
    
    async def discover_products_in_category(self, page, category_url):
        """Discover all product links in a category page"""
        product_links = set()
        
        if not await self.human_like_navigation(page, category_url):
            return product_links
        
        try:
            # Wait for product listings
            await page.wait_for_selector('.nf__part', timeout=10000)
            
            # Get all product links
            product_elements = await page.query_selector_all('.nf__part .nf__part__detail__title')
            
            for element in product_elements:
                href = await element.get_attribute('href')
                if href:
                    full_url = urljoin(self.base_url, href)
                    product_links.add(full_url)
            
            logger.info(f"🔍 Found {len(product_links)} products in {category_url}")
            
        except Exception as e:
            logger.info(f"⚠️ No products found in {category_url} or page structure different")
        
        return product_links
    
    async def extract_product_info(self, page, product_url, category):
        """Extract detailed product information"""
        if product_url in self.visited_urls:
            return None
            
        self.visited_urls.add(product_url)
        
        if not await self.human_like_navigation(page, product_url):
            return None
        
        try:
            # Extract part number from URL
            part_number_match = re.search(r'PS(\d+)', product_url)
            part_number = f"PS{part_number_match.group(1)}" if part_number_match else ""
            
            # Wait for key elements
            try:
                await page.wait_for_selector('h1', timeout=10000)
            except:
                logger.warning(f"⚠️ Page elements may not have loaded for {product_url}")
            
            # Extract name
            name = ""
            name_selectors = ['h1.pd__title', 'h1', '.product-title']
            for selector in name_selectors:
                try:
                    element = await page.query_selector(selector)
                    if element:
                        name = await element.text_content()
                        name = name.strip() if name else ""
                        if name:
                            break
                except:
                    continue
            
            # Extract description
            description = ""
            desc_selectors = ['.pd__description', '.description', '.product-description', 'div.col-md-6.mt-3']
            for selector in desc_selectors:
                try:
                    element = await page.query_selector(selector)
                    if element:
                        desc_text = await element.text_content()
                        if desc_text and len(desc_text.strip()) > 50:  # Get meaningful description
                            description = desc_text.strip()
                            break
                except:
                    continue
            
            # Extract price
            price = 0.0
            price_selectors = ['.pd__price .js-partPrice', '.pd__price', '.price', '.product-price', 'span[itemprop="price"]']
            for selector in price_selectors:
                try:
                    element = await page.query_selector(selector)
                    if element:
                        price_text = await element.text_content()
                        if price_text:
                            price_match = re.search(r'\$?([\d,]+\.?\d{0,2})', price_text)
                            if price_match:
                                price = float(price_match.group(1).replace(',', ''))
                                break
                except:
                    continue
            
            # Extract brand
            brand = ""
            brand_selectors = ['.pd__brand', '.brand', '[itemprop="brand"] [itemprop="name"]', 'span[itemprop="brand"] span[itemprop="name"]']
            for selector in brand_selectors:
                try:
                    element = await page.query_selector(selector)
                    if element:
                        brand = await element.text_content()
                        brand = brand.strip().replace('Brand:', '').strip() if brand else ""
                        if brand:
                            break
                except:
                    continue
            
            # Extract brand from name if not found
            if not brand and name:
                brand_patterns = ['Whirlpool', 'Frigidaire', 'GE', 'General Electric', 'Bosch', 'KitchenAid', 
                                'Maytag', 'Samsung', 'LG', 'Electrolux', 'Kenmore', 'Amana']
                for pattern in brand_patterns:
                    if pattern.lower() in name.lower():
                        brand = pattern
                        break
            
            # Extract image URL
            image_url = ""
            img_selectors = ['.pd__image img', '.product-image img', 'img[data-testid="product-image"]', 'img[itemprop="image"]']
            for selector in img_selectors:
                try:
                    element = await page.query_selector(selector)
                    if element:
                        src = await element.get_attribute('src')
                        if src and not src.startswith('data:') and 'logo' not in src.lower():
                            image_url = src if src.startswith('http') else urljoin(self.base_url, src)
                            break
                except:
                    continue
            
            # Extract compatibility models
            compatibility_models = []
            try:
                # Look for model numbers in specific sections and page content
                model_sections = await page.query_selector_all('.pd__wrap .col-md-6, .compatibility')
                for section in model_sections:
                    section_text = await section.text_content()
                    if section_text:
                        model_matches = re.findall(r'\b[A-Z]{2,4}\d{6,}[A-Z]?\d?\b', section_text)
                        compatibility_models.extend(model_matches)
                
                # Deduplicate and limit
                compatibility_models = list(set(compatibility_models[:15]))
            except:
                pass
            
            # Extract installation guide info with YouTube video links
            installation_guide = f"Please refer to the product manual or visit {product_url}#Instructions for detailed installation instructions."
            youtube_videos = []
            
            try:
                # CORRECT METHOD: Look for YouTube video thumbnails in product image gallery
                logger.info(f"🔍 Looking for YouTube video thumbnails for {part_number}...")
                
                # Method 1: Look for YouTube thumbnail images with data-src attributes
                thumbnail_elements = await page.query_selector_all('img[data-src*="youtube.com/vi/"], img[src*="youtube.com/vi/"]')
                for thumbnail in thumbnail_elements:
                    data_src = await thumbnail.get_attribute('data-src') or await thumbnail.get_attribute('src')
                    if data_src and 'youtube.com/vi/' in data_src:
                        logger.info(f"Found YouTube thumbnail: {data_src}")
                        # Extract video ID from thumbnail URL: https://img.youtube.com/vi/VIDEO_ID/maxresdefault.jpg
                        video_id_match = re.search(r'youtube\.com/vi/([a-zA-Z0-9_-]+)', data_src)
                        if video_id_match:
                            video_id = video_id_match.group(1)
                            youtube_url = f"https://www.youtube.com/watch?v={video_id}"
                            youtube_videos.append(youtube_url)
                            logger.info(f"✅ Extracted YouTube video: {youtube_url}")
                
                # Method 2: Backup - Check for iframe embeds
                iframe_elements = await page.query_selector_all('iframe[src*="youtube.com"], iframe[src*="youtu.be"]')
                for iframe in iframe_elements:
                    src = await iframe.get_attribute('src')
                    if src:
                        # Convert embed URLs to standard YouTube URLs
                        if 'youtube.com/embed/' in src:
                            video_id = src.split('/embed/')[-1].split('?')[0]
                            youtube_url = f"https://www.youtube.com/watch?v={video_id}"
                            if youtube_url not in youtube_videos:
                                youtube_videos.append(youtube_url)
                        elif 'youtu.be/' in src:
                            video_id = src.split('youtu.be/')[-1].split('?')[0]
                            youtube_url = f"https://www.youtube.com/watch?v={video_id}"
                            if youtube_url not in youtube_videos:
                                youtube_videos.append(youtube_url)
                
                # Method 3: Check for direct links to YouTube videos (but filter out general channel links)
                link_elements = await page.query_selector_all('a[href*="youtube.com/watch"], a[href*="youtu.be/"]')
                for link in link_elements:
                    href = await link.get_attribute('href')
                    if href and ('youtube.com/watch' in href or 'youtu.be/' in href):
                        # Skip general PartSelect channel links
                        if 'youtube.com/partselect' not in href.lower() and href not in youtube_videos:
                            youtube_videos.append(href)
                
                # Log results
                if youtube_videos:
                    logger.info(f"🎬 Found {len(youtube_videos)} YouTube video(s) for {part_number}")
                    for video in youtube_videos:
                        logger.info(f"   - {video}")
                else:
                    logger.info(f"❌ No YouTube videos found for {part_number}")
                    
            except Exception as e:
                logger.warning(f"Error extracting YouTube videos for {part_number}: {e}")
            
            try:
                # Extract installation difficulty and time info
                install_elements = await page.query_selector_all('.d-flex p, .install-info, .difficulty, .install-difficulty, .repair-difficulty')
                install_info = []
                for element in install_elements:
                    text = await element.text_content()
                    if text and any(keyword in text.lower() for keyword in ['difficulty', 'time', 'install', 'repair', 'easy', 'moderate', 'hard']):
                        install_info.append(text.strip())
                
                # Build comprehensive installation guide
                guide_parts = []
                if install_info:
                    guide_parts.append(' | '.join(install_info))
                
                if youtube_videos:
                    unique_videos = list(set(youtube_videos))  # Remove duplicates
                    video_text = "Installation Video(s): " + " | ".join(unique_videos)
                    guide_parts.append(video_text)
                
                guide_parts.append(f"Full instructions: {product_url}#Instructions")
                installation_guide = ' | '.join(guide_parts)
                
            except Exception as e:
                logger.warning(f"Error processing installation info: {e}")
                # Fallback - at least include YouTube videos if found
                if youtube_videos:
                    unique_videos = list(set(youtube_videos))
                    installation_guide = f"Installation Video(s): {' | '.join(unique_videos)} | Full instructions: {product_url}#Instructions"
            
            # Extract specifications
            specifications = {
                "part_number": part_number,
                "category": category,
                "url": product_url
            }
            
            try:
                # Look for specification tables or lists
                spec_elements = await page.query_selector_all('.specifications tr, .specs tr, .product-specs li')
                for element in spec_elements:
                    spec_text = await element.text_content()
                    if spec_text and ':' in spec_text:
                        parts = spec_text.split(':', 1)
                        if len(parts) == 2:
                            key = parts[0].strip()
                            value = parts[1].strip()
                            specifications[key] = value
            except:
                pass
            
            # Determine stock status
            in_stock = price > 0
            try:
                stock_elements = await page.query_selector_all('[itemprop="availability"], .stock-status, .availability')
                for element in stock_elements:
                    stock_text = await element.text_content()
                    if stock_text:
                        if 'out of stock' in stock_text.lower() or 'unavailable' in stock_text.lower():
                            in_stock = False
                        elif 'in stock' in stock_text.lower() or 'available' in stock_text.lower():
                            in_stock = True
            except:
                pass
            
            product = Product(
                part_number=part_number,
                name=name,
                description=description,
                price=price,
                brand=brand,
                category=category,
                image_url=image_url,
                product_url=product_url,
                compatibility_models=compatibility_models,
                installation_guide=installation_guide,
                specifications=specifications,
                in_stock=in_stock
            )
            
            logger.info(f"✅ Extracted: {part_number} - {name} - ${price} ({brand})")
            return product
            
        except Exception as e:
            logger.error(f"❌ Error extracting product {product_url}: {e}")
            return None
    
    async def scrape_all_category_products(self, category, main_category_url):
        """Scrape all products from a category comprehensively"""
        products = []
        
        async with async_playwright() as p:
            browser, context = await self.create_stealth_context(p)
            page = await context.new_page()
            
            try:
                logger.info(f"🚀 Starting comprehensive scraping for {category}")
                
                # Step 1: Discover all category/brand links
                logger.info("📂 Step 1: Discovering category links...")
                category_links = await self.discover_category_links(page, main_category_url)
                
                # Add the main category URL itself
                category_links.add(main_category_url)
                
                logger.info(f"📊 Found {len(category_links)} categories to explore")
                
                # Step 2: Discover all products in each category
                all_product_links = set()
                for i, cat_url in enumerate(category_links, 1):
                    logger.info(f"🔍 Step 2: Exploring category {i}/{len(category_links)}: {cat_url}")
                    
                    product_links = await self.discover_products_in_category(page, cat_url)
                    all_product_links.update(product_links)
                    
                    # Small delay between categories
                    await asyncio.sleep(random.uniform(2, 4))
                
                logger.info(f"🎯 Total products discovered: {len(all_product_links)}")
                
                # Step 3: Scrape each product
                for i, product_url in enumerate(all_product_links, 1):
                    logger.info(f"📦 Step 3: Scraping product {i}/{len(all_product_links)}")
                    
                    product = await self.extract_product_info(page, product_url, category)
                    if product:
                        products.append(product)
                    
                    # Progressive saving every 10 products
                    if len(products) % 10 == 0:
                        logger.info(f"💾 Progress save: {len(products)} products collected so far")
                        self.save_to_json(products, f'/Users/anujpatel/Study/Projects/InstalilyTask/scraping/data/{category.lower()}_parts_progress.json')
                    
                    # Delay between products
                    await asyncio.sleep(random.uniform(3, 6))
                
            finally:
                await browser.close()
        
        return products
    
    def save_to_json(self, products: List[Product], filename: str):
        """Save products to JSON file"""
        data = [asdict(product) for product in products]
        
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        
        logger.info(f"💾 Saved {len(products)} products to {filename}")
    
    def save_to_csv(self, products: List[Product], filename: str):
        """Save products to CSV file"""
        if not products:
            logger.warning("No products to save")
            return
            
        fieldnames = [
            'part_number', 'name', 'description', 'price', 'brand', 'category',
            'image_url', 'product_url', 'compatibility_models', 'installation_guide',
            'specifications', 'in_stock'
        ]
        
        with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            
            for product in products:
                row = asdict(product)
                # Convert complex fields to strings
                row['compatibility_models'] = ';'.join(product.compatibility_models)
                row['specifications'] = json.dumps(product.specifications)
                writer.writerow(row)
        
        logger.info(f"💾 Saved {len(products)} products to {filename}")

async def main():
    """Main comprehensive scraping function"""
    scraper = ComprehensivePartsScraper()
    
    categories_to_scrape = [
        {
            'name': 'refrigerator',
            'url': 'https://www.partselect.com/Refrigerator-Parts.htm'
        },
        {
            'name': 'dishwasher', 
            'url': 'https://www.partselect.com/Dishwasher-Parts.htm'
        }
    ]
    
    all_products = []
    
    for category_info in categories_to_scrape:
        category_name = category_info['name']
        category_url = category_info['url']
        
        logger.info(f"🎯 Starting {category_name.upper()} scraping...")
        category_products = await scraper.scrape_all_category_products(category_name, category_url)
        
        all_products.extend(category_products)
        
        # Save category-specific files
        if category_products:
            scraper.save_to_json(category_products, f'/Users/anujpatel/Study/Projects/InstalilyTask/scraping/data/{category_name}_parts.json')
            scraper.save_to_csv(category_products, f'/Users/anujpatel/Study/Projects/InstalilyTask/scraping/data/{category_name}_parts.csv')
        
        logger.info(f"✅ {category_name.upper()} scraping completed: {len(category_products)} products")
        
        # Long delay between categories to be respectful
        if category_info != categories_to_scrape[-1]:
            delay = random.uniform(10, 20)
            logger.info(f"⏳ Waiting {delay:.1f} seconds before next category...")
            await asyncio.sleep(delay)
    
    # Save combined data
    if all_products:
        scraper.save_to_json(all_products, '/Users/anujpatel/Study/Projects/InstalilyTask/scraping/data/all_parts.json')
        scraper.save_to_csv(all_products, '/Users/anujpatel/Study/Projects/InstalilyTask/scraping/data/all_parts.csv')
    
    logger.info(f"🎉 COMPREHENSIVE SCRAPING COMPLETED!")
    logger.info(f"📊 Total products scraped: {len(all_products)}")
    
    # Summary by category
    refrigerator_count = len([p for p in all_products if p.category == 'refrigerator'])
    dishwasher_count = len([p for p in all_products if p.category == 'dishwasher'])
    
    logger.info(f"🧊 Refrigerator parts: {refrigerator_count}")
    logger.info(f"🍽️  Dishwasher parts: {dishwasher_count}")

if __name__ == "__main__":
    asyncio.run(main())
