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
from urllib.parse import urljoin, urlparse, parse_qs

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

@dataclass
class BlogPost:
    title: str
    url: str
    excerpt: str
    author: str
    date: str
    category: str
    tags: List[str]
    content: str
    image_url: str

class ComprehensiveBlogScraper:
    def __init__(self):
        self.base_url = "https://www.partselect.com"
        self.blog_base_url = "https://www.partselect.com/content/blog"
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
            
            Object.defineProperty(navigator, 'plugins', {
                get: () => [1, 2, 3, 4, 5],
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
            
            # Scroll to load content
            await page.evaluate('window.scrollTo(0, document.body.scrollHeight/3)')
            await page.wait_for_timeout(random.randint(1000, 2000))
            
            await page.evaluate('window.scrollTo(0, document.body.scrollHeight/2)')
            await page.wait_for_timeout(random.randint(1000, 2000))
            
            return True
        except Exception as e:
            logger.error(f"❌ Navigation failed: {e}")
            return False
    
    async def discover_blog_pages(self, page):
        """Discover all blog list pages"""
        if not await self.human_like_navigation(page, self.blog_base_url):
            return []
        
        blog_pages = [self.blog_base_url]
        
        try:
            # Look for pagination
            pagination_selectors = [
                '.pagination a',
                '.page-numbers a', 
                '.nav-links a',
                'a[href*="start="]',
                'a[href*="page="]'
            ]
            
            for selector in pagination_selectors:
                try:
                    pagination_links = await page.query_selector_all(selector)
                    if pagination_links:
                        logger.info(f"📄 Found pagination with selector: {selector}")
                        
                        for link in pagination_links:
                            href = await link.get_attribute('href')
                            if href:
                                # Extract page numbers or start parameters
                                if 'start=' in href or 'page=' in href:
                                    full_url = urljoin(self.base_url, href)
                                    blog_pages.append(full_url)
                        break
                except:
                    continue
            
            # If no pagination found, try generating pages based on start parameter
            if len(blog_pages) == 1:
                logger.info("📄 No pagination found, generating page URLs...")
                for start in range(2, 25):  # Try up to page 25
                    blog_pages.append(f"{self.blog_base_url}?start={start}")
            
            # Remove duplicates while preserving order
            seen = set()
            unique_pages = []
            for page_url in blog_pages:
                if page_url not in seen:
                    seen.add(page_url)
                    unique_pages.append(page_url)
            
            logger.info(f"📊 Discovered {len(unique_pages)} blog pages to scrape")
            return unique_pages
            
        except Exception as e:
            logger.error(f"❌ Error discovering blog pages: {e}")
            return blog_pages
    
    async def extract_blog_links_from_page(self, page, blog_list_url):
        """Extract individual blog post links from a blog list page"""
        if not await self.human_like_navigation(page, blog_list_url):
            return []
        
        blog_links = []
        
        try:
            # Wait for blog container
            await page.wait_for_selector('div[role="main"].blog', timeout=10000)
            
            # Multiple selectors for blog post links
            blog_selectors = [
                'a.blog__hero-article',
                'a.article-card', 
                '.blog-post a',
                '.post-title a',
                'article a',
                '.entry-title a',
                'h2 a',
                'h3 a'
            ]
            
            links_found = False
            for selector in blog_selectors:
                try:
                    elements = await page.query_selector_all(selector)
                    if elements:
                        logger.info(f"🔗 Found {len(elements)} blog links with selector: {selector}")
                        
                        for element in elements:
                            href = await element.get_attribute('href')
                            if href and '/blog/' in href:
                                full_url = urljoin(self.base_url, href)
                                if full_url not in self.visited_urls:
                                    blog_links.append(full_url)
                        
                        links_found = True
                        break
                except:
                    continue
            
            if not links_found:
                logger.warning(f"⚠️ No blog links found on {blog_list_url}")
            
        except Exception as e:
            logger.error(f"❌ Error extracting blog links from {blog_list_url}: {e}")
        
        return blog_links
    
    async def extract_blog_content(self, page, blog_url):
        """Extract detailed content from a blog post"""
        if blog_url in self.visited_urls:
            return None
            
        self.visited_urls.add(blog_url)
        
        if not await self.human_like_navigation(page, blog_url):
            return None
        
        try:
            # Extract title
            title = ""
            title_selectors = ['h1', '.entry-title', '.post-title', '.blog-title', '.article-title']
            for selector in title_selectors:
                try:
                    element = await page.query_selector(selector)
                    if element:
                        title = await element.text_content()
                        title = title.strip() if title else ""
                        if title:
                            break
                except:
                    continue
            
            # Extract from URL if no title found
            if not title:
                url_path = blog_url.split('/blog/')[-1].rstrip('/')
                title = url_path.replace('-', ' ').title()
            
            # Extract excerpt/summary
            excerpt = ""
            excerpt_selectors = ['.excerpt', '.summary', '.post-excerpt', '.entry-summary', 'p']
            for selector in excerpt_selectors:
                try:
                    element = await page.query_selector(selector)
                    if element:
                        excerpt_text = await element.text_content()
                        if excerpt_text and len(excerpt_text.strip()) > 50:
                            excerpt = excerpt_text.strip()[:300] + "..." if len(excerpt_text) > 300 else excerpt_text.strip()
                            break
                except:
                    continue
            
            # Extract author
            author = "PartSelect Team"
            author_selectors = ['.author', '.by-author', '.post-author', '.entry-author']
            for selector in author_selectors:
                try:
                    element = await page.query_selector(selector)
                    if element:
                        author_text = await element.text_content()
                        if author_text:
                            author = author_text.strip()
                            break
                except:
                    continue
            
            # Extract date
            date = ""
            date_selectors = ['.date', '.post-date', '.entry-date', '.published', 'time']
            for selector in date_selectors:
                try:
                    element = await page.query_selector(selector)
                    if element:
                        date_text = await element.text_content()
                        if date_text:
                            date = date_text.strip()
                            break
                except:
                    continue
            
            # Extract category
            category = "Appliance Repair"
            category_selectors = ['.category', '.post-category', '.entry-category']
            for selector in category_selectors:
                try:
                    element = await page.query_selector(selector)
                    if element:
                        cat_text = await element.text_content()
                        if cat_text:
                            category = cat_text.strip()
                            break
                except:
                    continue
            
            # Extract tags
            tags = []
            tag_selectors = ['.tags a', '.post-tags a', '.entry-tags a']
            for selector in tag_selectors:
                try:
                    elements = await page.query_selector_all(selector)
                    for element in elements:
                        tag_text = await element.text_content()
                        if tag_text:
                            tags.append(tag_text.strip())
                except:
                    continue
            
            # Extract main content
            content = ""
            content_selectors = ['.content', '.post-content', '.entry-content', '.article-content', 'main']
            for selector in content_selectors:
                try:
                    element = await page.query_selector(selector)
                    if element:
                        content_text = await element.text_content()
                        if content_text and len(content_text.strip()) > 100:
                            content = content_text.strip()
                            break
                except:
                    continue
            
            # Extract featured image
            image_url = ""
            img_selectors = ['.featured-image img', '.post-image img', '.entry-image img', '.hero-image img', 'article img']
            for selector in img_selectors:
                try:
                    element = await page.query_selector(selector)
                    if element:
                        src = await element.get_attribute('src')
                        if src and not src.startswith('data:'):
                            image_url = src if src.startswith('http') else urljoin(self.base_url, src)
                            break
                except:
                    continue
            
            blog_post = BlogPost(
                title=title,
                url=blog_url,
                excerpt=excerpt,
                author=author,
                date=date,
                category=category,
                tags=tags,
                content=content,
                image_url=image_url
            )
            
            logger.info(f"✅ Extracted blog: {title}")
            return blog_post
            
        except Exception as e:
            logger.error(f"❌ Error extracting blog content from {blog_url}: {e}")
            return None
    
    async def scrape_all_blogs(self):
        """Scrape all blog posts comprehensively"""
        all_blogs = []
        
        async with async_playwright() as p:
            browser, context = await self.create_stealth_context(p)
            page = await context.new_page()
            
            try:
                logger.info("🚀 Starting comprehensive blog scraping...")
                
                # Step 1: Discover all blog list pages
                logger.info("📄 Step 1: Discovering blog list pages...")
                blog_pages = await self.discover_blog_pages(page)
                
                # Step 2: Extract blog post links from each page
                all_blog_links = []
                for i, blog_page_url in enumerate(blog_pages, 1):
                    logger.info(f"🔍 Step 2: Extracting links from page {i}/{len(blog_pages)}")
                    
                    blog_links = await self.extract_blog_links_from_page(page, blog_page_url)
                    all_blog_links.extend(blog_links)
                    
                    logger.info(f"📝 Found {len(blog_links)} blog posts on page {i}")
                    
                    # Delay between pages
                    await asyncio.sleep(random.uniform(3, 5))
                    
                    # Stop if we haven't found any blogs on recent pages
                    if i > 5 and len(blog_links) == 0:
                        logger.info("📄 No more blogs found, stopping page discovery")
                        break
                
                # Remove duplicates
                unique_blog_links = list(set(all_blog_links))
                logger.info(f"📊 Total unique blog posts discovered: {len(unique_blog_links)}")
                
                # Step 3: Extract content from each blog post
                for i, blog_url in enumerate(unique_blog_links, 1):
                    logger.info(f"📖 Step 3: Scraping blog {i}/{len(unique_blog_links)}")
                    
                    blog_post = await self.extract_blog_content(page, blog_url)
                    if blog_post:
                        all_blogs.append(blog_post)
                    
                    # Progress save every 5 blogs
                    if len(all_blogs) % 5 == 0:
                        logger.info(f"💾 Progress save: {len(all_blogs)} blogs collected")
                        self.save_to_json(all_blogs, '/Users/anujpatel/Study/Projects/InstalilyTask/scraping/data/blogs_progress.json')
                    
                    # Delay between blog posts
                    await asyncio.sleep(random.uniform(3, 6))
                
            finally:
                await browser.close()
        
        return all_blogs
    
    def save_to_json(self, blogs: List[BlogPost], filename: str):
        """Save blogs to JSON file"""
        data = [asdict(blog) for blog in blogs]
        
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        
        logger.info(f"💾 Saved {len(blogs)} blogs to {filename}")
    
    def save_to_csv(self, blogs: List[BlogPost], filename: str):
        """Save blogs to CSV file"""
        if not blogs:
            logger.warning("No blogs to save")
            return
            
        fieldnames = ['title', 'url', 'excerpt', 'author', 'date', 'category', 'tags', 'content', 'image_url']
        
        with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            
            for blog in blogs:
                row = asdict(blog)
                # Convert tags list to string
                row['tags'] = ';'.join(blog.tags)
                writer.writerow(row)
        
        logger.info(f"💾 Saved {len(blogs)} blogs to {filename}")

async def main():
    """Main blog scraping function"""
    scraper = ComprehensiveBlogScraper()
    
    logger.info("📚 Starting comprehensive blog scraping...")
    blogs = await scraper.scrape_all_blogs()
    
    if blogs:
        # Save to both formats
        scraper.save_to_json(blogs, '/Users/anujpatel/Study/Projects/InstalilyTask/scraping/data/all_blogs.json')
        scraper.save_to_csv(blogs, '/Users/anujpatel/Study/Projects/InstalilyTask/scraping/data/all_blogs.csv')
        
        logger.info(f"🎉 BLOG SCRAPING COMPLETED!")
        logger.info(f"📚 Total blogs scraped: {len(blogs)}")
        
        # Summary stats
        categories = {}
        for blog in blogs:
            categories[blog.category] = categories.get(blog.category, 0) + 1
        
        logger.info("📊 Blog categories:")
        for category, count in categories.items():
            logger.info(f"   {category}: {count} posts")
    else:
        logger.warning("❌ No blogs were collected")

if __name__ == "__main__":
    asyncio.run(main())
