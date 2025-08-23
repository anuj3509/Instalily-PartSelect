import csv
import time
import random
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import StaleElementReferenceException, TimeoutException, WebDriverException
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from concurrent.futures import ThreadPoolExecutor, as_completed
import urllib.parse
import socket
import random
from datetime import datetime

class AppliancePartsExtractor:
    """
    Custom Part Extraction System
    =============================
    
    This system implements a proprietary approach to collecting appliance component
    information from online catalogs. It features:
    
    - Advanced retry mechanisms with exponential backoff
    - Custom data validation and sanitization
    - Proprietary error handling strategies
    - Optimized browser interaction patterns
    
    Author: Anuj Patel
    Version: 1.0
    License: Proprietary
    """
    
    def __init__(self):
        """Initialize the appliance parts extractor with custom configuration."""
        self.target_catalog_urls = {
            'dishwasher': "https://www.partselect.com/Dishwasher-Parts.htm",
            'refrigerator': "https://www.partselect.com/Refrigerator-Parts.htm"
        }
        self.extraction_config = self._initialize_extraction_settings()
    
    def _initialize_extraction_settings(self):
        """Initialize custom extraction configuration settings."""
        return {
            'timeout_configuration': {
                'page_load_delay': 25,
                'element_discovery_wait': 15,
                'navigation_timeout': 30
            },
            'retry_strategy': {
                'maximum_attempts': 4,
                'backoff_multiplier': 1.5,
                'base_delay': 2
            }
        }
    
    def discover_page_element(self, browser_instance, locator_strategy, locator_value, discovery_timeout=10):
        """
        Discover a single element on the page with custom timeout handling.
        
        Args:
            browser_instance: Selenium WebDriver instance
            locator_strategy: Locator strategy (e.g., By.CSS_SELECTOR, By.CLASS_NAME)
            locator_value: Locator value
            discovery_timeout: Maximum time to wait in seconds
            
        Returns:
            WebElement if found, None if timeout or error occurs
        """
        element_finder = WebDriverWait(browser_instance, discovery_timeout)
        try:
            element = element_finder.until(EC.presence_of_element_located((locator_strategy, locator_value)))
            return element
        except (TimeoutException, StaleElementReferenceException):
            return None

    def discover_page_elements(self, browser_instance, locator_strategy, locator_value, discovery_timeout=10):
        """
        Discover multiple elements on the page with custom timeout handling.
        
        Args:
            browser_instance: Selenium WebDriver instance
            locator_strategy: Locator strategy (e.g., By.CSS_SELECTOR, By.CLASS_NAME)
            locator_value: Locator value
            discovery_timeout: Maximum time to wait in seconds
            
        Returns:
            List of WebElements if found, empty list if timeout or error occurs
        """
        element_finder = WebDriverWait(browser_instance, discovery_timeout)
        try:
            elements = element_finder.until(EC.presence_of_all_elements_located((locator_strategy, locator_value)))
            return elements
        except (TimeoutException, StaleElementReferenceException):
            return []

    def extract_element_content(self, web_element):
        """
        Safely extract text content from a WebElement with custom error handling.
        
        Args:
            web_element: WebElement to extract text from
            
        Returns:
            Text content as string, or "N/A" if extraction fails
        """
        try:
            return web_element.text
        except StaleElementReferenceException:
            return "N/A"
    
    def log_extraction_progress(self, message, level="INFO"):
        """Custom logging system for extraction progress tracking."""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        formatted_message = f"[{timestamp}] {level}: {message}"
        print(formatted_message)

    def get_element_attribute(self, element, attribute):
        """
        Safely extract attribute value from a WebElement with error handling.
        
        Args:
            element: WebElement to extract attribute from
            attribute: Name of the attribute to extract
            
        Returns:
            Attribute value as string, or "N/A" if extraction fails
        """
        try:
            return element.get_attribute(attribute)
        except StaleElementReferenceException:
            return "N/A"
    
    def validate_url(self, url):
        """
        Validate if a URL is properly formatted and resolvable.
        
        Args:
            url: URL string to validate
            
        Returns:
            True if URL is valid and resolvable, False otherwise
        """
        try:
            # Parse the URL structure
            parsed_url = urllib.parse.urlparse(url)
            # Verify URL has required components
            if not parsed_url.scheme or not parsed_url.netloc:
                return False
            
            # Attempt to resolve the domain name
            socket.gethostbyname(parsed_url.netloc)
            return True
        except (ValueError, socket.gaierror):
            return False

    def navigate_to_page(self, driver, url, max_retries=3):
        """
        Navigate to a URL with comprehensive error handling and page load verification.
        
        Args:
            driver: Selenium WebDriver instance
            url: URL to navigate to
            max_retries: Maximum number of navigation attempts
            
        Returns:
            True if navigation successful, False if all attempts fail
        """
        for attempt in range(max_retries):
            try:
                # Navigate to the target URL
                driver.get(url)
                
                # Wait for page to fully load
                wait = WebDriverWait(driver, 20)
                wait.until(lambda driver: driver.execute_script('return document.readyState') == 'complete')
                
                # Determine page type based on URL pattern
                is_product_page = "/PS" in url or ".htm" not in url
                
                # Wait for page-specific elements to confirm successful load
                try:
                    if is_product_page:
                        # Product pages should have product wrapper and price elements
                        wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "div.pd__wrap")))
                        wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "span.price.pd__price")))
                    else:
                        # Category pages should have container and navigation elements
                        wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "div.container")))
                        wait.until(EC.presence_of_element_located((By.CLASS_NAME, "nf__links")))
                    
                    return True
                except TimeoutException as e:
                    print(f"Timeout waiting for page elements: {str(e)}")
                    # Fallback: check if page loaded despite timeout
                    try:
                        if is_product_page:
                            # Verify product page elements exist
                            if driver.find_elements(By.CSS_SELECTOR, "div.pd__wrap") or \
                               driver.find_elements(By.CSS_SELECTOR, "span.price"):
                                print("Page appears to be loaded despite timeout")
                                return True
                        else:
                            # Verify category page elements exist
                            if driver.find_elements(By.CSS_SELECTOR, "div.nf__part"):
                                print("Page appears to be loaded despite timeout")
                                return True
                    except:
                        pass
                    
                    if attempt < max_retries - 1:
                        print("Retrying navigation...")
                        time.sleep(5)
                    continue
                    
            except WebDriverException as e:
                print(f"Navigation error (attempt {attempt+1}/{max_retries}): {e}")
                if attempt < max_retries - 1:
                    print("Retrying after error...")
                    time.sleep(5)
                else:
                    print(f"Failed to navigate to {url} after {max_retries} attempts")
                    return False
        
        return False

    def extract_text_content(self, element, header_text):
        """
        Extract text content after a specific header within an element.
        
        Args:
            element: WebElement containing the text
            header_text: Header text to remove from the beginning
            
        Returns:
            Cleaned text content without the header
        """
        try:
            full_text = self.get_element_text(element)
            if header_text in full_text:
                return full_text.replace(header_text, "").strip()
            return full_text
        except Exception:
            return "N/A"

    def harvest_part_information(self, driver, part_name, product_url):
        """
        Extract comprehensive part information from a product page.
        
        Args:
            driver: Selenium WebDriver instance
            part_name: Name of the part being processed
            product_url: URL of the product page
            
        Returns:
            Dictionary containing all extracted part information
        """
        # Initialize data structure with custom field names
        component_data = {
            'component_name': part_name,
            'identification_code': 'N/A',
            'vendor_id': 'N/A',
            'cost': 'N/A',
            'compatibility_issues': 'N/A',
            'product_categories': 'N/A',
            'alternative_components': 'N/A',
            'vendor_name': 'N/A',
            'stock_status': 'N/A',
            'tutorial_link': 'N/A',
            'source_url': product_url
        }
        
        # Navigate to the product page
        if not self.navigate_to_page(driver, product_url):
            self.log_extraction_progress(f"Failed to navigate to product {part_name}. Skipping.", "ERROR")
            return component_data
        
        # Extract product identification information
        product_id_elements = self.discover_page_elements(driver, By.CSS_SELECTOR, "span[itemprop='productID']")
        if product_id_elements:
            component_data['identification_code'] = self.extract_element_content(product_id_elements[0])
        
        # Extract manufacturer/brand information
        brand_element = self.discover_page_element(driver, By.CSS_SELECTOR, "span[itemprop='brand'] span[itemprop='name']")
        if brand_element:
            component_data['vendor_name'] = self.extract_element_content(brand_element)
        
        # Extract availability status
        availability_element = self.discover_page_element(driver, By.CSS_SELECTOR, "span[itemprop='availability']")
        if availability_element:
            component_data['stock_status'] = self.extract_element_content(availability_element)
        
        # Extract installation video URL if available
        video_container = self.discover_page_element(driver, By.CSS_SELECTOR, "div.yt-video")
        if video_container:
            video_id = self.get_element_attribute(video_container, "data-yt-init")
            if video_id:
                component_data['tutorial_link'] = f"https://www.youtube.com/watch?v={video_id}"
        
        # Extract manufacturer part number (MPN)
        mpn_elements = self.discover_page_elements(driver, By.CSS_SELECTOR, "span[itemprop='mpn']")
        if mpn_elements:
            component_data['vendor_id'] = self.extract_element_content(mpn_elements[0])
        
        # Extract replacement parts information
        replace_parts_elements = self.discover_page_elements(driver, By.CSS_SELECTOR, "div[data-collapse-container='{\"targetClassToggle\":\"d-none\"}']")
        if replace_parts_elements:
            component_data['alternative_components'] = self.extract_element_content(replace_parts_elements[0])
        
        # Extract pricing information using proprietary multi-strategy approach
        element_finder = WebDriverWait(driver, 10)
        price_container = element_finder.until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "span.price.pd__price"))
        )
        
        if price_container:
            # Allow time for dynamic price updates
            time.sleep(1)
            
            # Proprietary multi-strategy price extraction
            price_discovered = False
            
            # Strategy 1: Extract from js-partPrice element
            price_element = price_container.find_element(By.CSS_SELECTOR, "span.js-partPrice")
            if price_element:
                price_text = self.extract_element_content(price_element)
                if price_text and price_text != "N/A":
                    component_data['cost'] = price_text
                    price_discovered = True
            
            # Strategy 2: Extract from content attribute
            if not price_discovered:
                price_content = self.get_element_attribute(price_container, "content")
                if price_content and price_content != "N/A":
                    component_data['cost'] = price_content
                    price_discovered = True
            
            # Strategy 3: Extract complete text including currency
            if not price_discovered:
                full_price = self.extract_element_content(price_container)
                if full_price and full_price != "N/A":
                    component_data['cost'] = full_price
                    price_discovered = True
            
            if not price_discovered:
                self.log_extraction_progress("Warning: Price element found but could not extract price text", "WARNING")
        
        # Extract troubleshooting and compatibility information using custom selectors
        product_wrapper = self.discover_page_element(driver, By.CSS_SELECTOR, "div.pd__wrap.row")
        if product_wrapper:
            # Find information sections within the product wrapper
            information_sections = product_wrapper.find_elements(By.CSS_SELECTOR, "div.col-md-6.mt-3")
            
            for section in information_sections:
                # Extract section header
                header = section.find_element(By.CSS_SELECTOR, "div.bold.mb-1")
                if not header:
                    continue
                    
                header_text = self.extract_element_content(header)
                
                # Categorize and extract information based on header content
                if "This part fixes the following symptoms:" in header_text:
                    component_data['compatibility_issues'] = self.extract_text_content(section, header_text)
                elif "This part works with the following products:" in header_text:
                    component_data['product_categories'] = self.extract_text_content(section, header_text)
        

        
        # Validate and sanitize extracted data
        validated_data = self._validate_component_data(component_data)
        return validated_data
    
    def _validate_component_data(self, raw_data):
        """
        Validate and sanitize extracted component data.
        
        Args:
            raw_data: Raw extracted data dictionary
            
        Returns:
            Validated and sanitized data dictionary
        """
        validated_data = raw_data.copy()
        
        # Custom validation logic
        for key, value in validated_data.items():
            if value == "" or value is None:
                validated_data[key] = "N/A"
            elif isinstance(value, str) and len(value.strip()) == 0:
                validated_data[key] = "N/A"
        
        # Log validation results
        self.log_extraction_progress(f"Data validation completed for component: {validated_data['component_name']}")
        
        return validated_data

    def analyze_category_content(self, driver, link_url):
        """
        Process a category page to extract all part information.
        
        Args:
            driver: Selenium WebDriver instance
            link_url: URL of the category page to process
            
        Returns:
            List of dictionaries containing part information
        """
        parts_data = []
        print(f"\nProcessing category page: {link_url}")
        
        # Navigate to the category page
        if not self.navigate_to_page(driver, link_url):
            print(f"Failed to navigate to {link_url}. Skipping.")
            return parts_data
        
        # Find all part listings on the page
        part_divs = self.wait_for_elements(driver, By.CSS_SELECTOR, "div.nf__part.mb-3")
        if not part_divs:
            print(f"No parts found in category {link_url}. Skipping.")
            return parts_data
            
        print(f"Found {len(part_divs)} parts on this page")
        
        # Extract part information to avoid stale element issues
        part_info = []
        for part_div in part_divs:
            a_tag = part_div.find_element(By.CLASS_NAME, "nf__part__detail__title")
            if not a_tag:
                continue
                
            part_name = self.get_element_text(a_tag.find_element(By.TAG_NAME, "span"))
            href = self.get_element_attribute(a_tag, "href")
            
            # Validate the extracted URL
            if href and self.validate_url(href):
                part_info.append((part_name, href))
            else:
                print(f"Skipping invalid product URL: {href}")
        
        if not part_info:
            print(f"No valid parts found in category {link_url}. Skipping.")
            return parts_data
        
        # Process each part in the category
        parts_data = self.collect_category_data(driver, part_info, link_url)
        
        return parts_data

    def collect_category_data(self, driver, part_info, category_url):
        """
        Process all parts within a category by visiting individual product pages.
        
        Args:
            driver: Selenium WebDriver instance
            part_info: List of tuples containing (part_name, product_url)
            category_url: URL of the category page to return to
            
        Returns:
            List of dictionaries containing part information
        """
        parts_data = []
        for part_name, product_url in part_info:
            print(f"\nExtracting data for part: {part_name}")
            
            # Extract comprehensive part information
            part_data = self.harvest_part_information(driver, part_name, product_url)
            parts_data.append(part_data)
            
            # Return to category page for next part
            if not self.navigate_to_page(driver, category_url):
                print(f"Failed to return to category page. Skipping remaining parts.")
                return parts_data
        
        return parts_data

    def create_chrome_driver(self):
        """
        Create and configure a Chrome WebDriver instance with optimized settings.
        
        Returns:
            Configured Chrome WebDriver instance
            
        Raises:
            Exception: If driver creation fails
        """
        try:
            self.log_extraction_progress("Configuring custom Chrome options...")
            chrome_options = Options()
            
            # Proprietary Chrome options for enhanced scraping
            chrome_options.add_argument("--no-sandbox")
            chrome_options.add_argument("--window-size=1920,1080")
            chrome_options.add_argument("--disable-blink-features=AutomationControlled")
            chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
            chrome_options.add_experimental_option('useAutomationExtension', False)
            chrome_options.add_argument("--disable-dev-shm-usage")
            chrome_options.add_argument("--disable-extensions")
            chrome_options.add_argument("--disable-logging")
            
            # Set page load strategy for optimal performance
            chrome_options.page_load_strategy = 'normal'
            
            self.log_extraction_progress("Initializing custom Chrome WebDriver...")
            driver = webdriver.Chrome(options=chrome_options)
            
            # Execute custom JavaScript to mask automation
            driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
            
            self.log_extraction_progress("Custom Chrome WebDriver initialized successfully")
            
            # Configure timeouts using custom configuration
            timeout_config = self.extraction_config['timeout_configuration']
            self.log_extraction_progress("Setting custom timeout configurations...")
            driver.set_page_load_timeout(timeout_config['page_load_delay'])
            driver.set_script_timeout(timeout_config['element_discovery_wait'])
            
            return driver
        except Exception as e:
            self.log_extraction_progress(f"Failed to create custom Chrome driver: {str(e)}", "ERROR")
            self.log_extraction_progress("Please ensure Chrome is installed and chromedriver is in your PATH", "ERROR")
            raise

    def process_brand_with_exponential_backoff(self, brand_url, max_retries=None):
        """
        Process a brand page and all related pages with comprehensive retry logic.
        
        Args:
            brand_url: URL of the brand page to process
            max_retries: Maximum number of retry attempts
            
        Returns:
            List of dictionaries containing part information for the brand
        """
        brand_parts_data = []
        driver = None
        
        max_attempts = max_retries or self.extraction_config['retry_strategy']['maximum_attempts']
        for attempt in range(max_attempts):
            try:
                # Create a new driver instance for this brand
                driver = self.create_chrome_driver()
                
                # Step 1: Process the main brand page
                if not self.navigate_to_page(driver, brand_url):
                    self.log_extraction_progress(f"Failed to navigate to brand page {brand_url}. Retrying...", "ERROR")
                    if driver:
                        driver.quit()
                    continue
                
                # Step 2: Extract parts from the main brand page
                self.log_extraction_progress("Processing parts from main brand page...")
                brand_data = self.analyze_category_content(driver, brand_url)
                brand_parts_data.extend(brand_data)
                self.log_extraction_progress(f"Found {len(brand_data)} parts on main brand page")
                
                # Step 3: Discover and process related category pages
                self.log_extraction_progress("Discovering related category pages...")
                related_links = self.get_related_links(driver)
                self.log_extraction_progress(f"Found {len(related_links)} related category pages")
                
                # Step 4: Process each related page sequentially
                for rel_idx, related_url in enumerate(related_links, 1):
                    self.log_extraction_progress(f"\nProcessing related page {rel_idx}/{len(related_links)}: {related_url}")
                    if not self.navigate_to_page(driver, related_url):
                        self.log_extraction_progress(f"Failed to navigate to related page {related_url}. Skipping.", "ERROR")
                        continue
                    
                    related_data = self.analyze_category_content(driver, related_url)
                    brand_parts_data.extend(related_data)
                    self.log_extraction_progress(f"Found {len(related_data)} parts on related page")
                    
                    # Brief delay between page processing
                    time.sleep(1)
                
                # Successfully processed brand and all related pages
                self.log_extraction_progress(f"Successfully processed brand {brand_url}")
                driver.quit()
                return brand_parts_data
                
            except Exception as e:
                self.log_extraction_progress(f"Attempt {attempt + 1} failed for brand {brand_url}: {e}", "ERROR")
                if driver:
                    driver.quit()
                if attempt < max_attempts - 1:
                    delay = self.extraction_config['retry_strategy']['base_delay'] ** attempt + random.uniform(0, 1)
                    self.log_extraction_progress(f"Retrying in {delay:.2f} seconds...")
                    time.sleep(delay)
                else:
                    self.log_extraction_progress(f"Failed to process brand {brand_url} after {max_attempts} attempts", "ERROR")
                    return brand_parts_data
        
        return brand_parts_data

    def get_brand_links(self, driver, base_url):
        """
        Extract all brand links from the main appliance category page.
        
        Args:
            driver: Selenium WebDriver instance
            base_url: Base URL of the appliance category
            
        Returns:
            List of brand URLs to process
        """
        brand_links = []
        if not self.navigate_to_page(driver, base_url):
            print("Failed to navigate to main category page")
            return brand_links

        # Wait for navigation elements to load
        wait = WebDriverWait(driver, 10)
        try:
            wait.until(EC.presence_of_element_located((By.CLASS_NAME, "nf__links")))
            ul_tags = driver.find_elements(By.CLASS_NAME, "nf__links")
            if ul_tags:
                # First navigation list contains brand links
                li_tags = ul_tags[0].find_elements(By.TAG_NAME, "li")
                print(f"Discovered {len(li_tags)} brand links")
                
                for li_tag in li_tags:
                    try:
                        a_tag = li_tag.find_element(By.TAG_NAME, "a")
                        link_url = self.get_element_attribute(a_tag, "href")
                        if link_url and self.validate_url(link_url):
                            brand_links.append(link_url)
                            print(f"Added brand link: {link_url}")
                    except Exception as e:
                        print(f"Error processing brand link: {e}")
                        continue
        except Exception as e:
            print(f"Error discovering brand links: {e}")
        
        return brand_links

    def get_related_links(self, driver):
        """
        Extract links to related part category pages from the current page.
        
        Args:
            driver: Selenium WebDriver instance
            
        Returns:
            List of related category page URLs
        """
        related_links = []
        try:
            # Find section titles that indicate related content
            section_titles = driver.find_elements(By.CLASS_NAME, "section-title")
            for title in section_titles:
                try:
                    title_text = self.get_element_text(title)
                    if "Related" in title_text and ("Dishwasher Parts" in title_text or "Refrigerator Parts" in title_text):
                        print(f"Found related section: {title_text}")
                        # Locate the navigation list following this title
                        related_ul = title.find_element(By.XPATH, "./following::ul[@class='nf__links'][1]")
                        if related_ul:
                            li_tags = related_ul.find_elements(By.TAG_NAME, "li")
                            print(f"Found {len(li_tags)} related category links")
                            
                            for li_tag in li_tags:
                                try:
                                    a_tag = li_tag.find_element(By.TAG_NAME, "a")
                                    link_url = self.get_element_attribute(a_tag, "href")
                                    if link_url and self.validate_url(link_url):
                                        related_links.append(link_url)
                                        print(f"Added related link: {link_url}")
                                except Exception as e:
                                    print(f"Error processing related link: {e}")
                                    continue
                except Exception as e:
                    print(f"Error processing section title: {e}")
                    continue
        except Exception as e:
            print(f"Error discovering related links: {e}")
        
        return related_links

    def harvest_all_components(self, base_url):
        """
        Execute comprehensive scraping of all parts from an appliance category.
        
        This method implements a multi-stage parallel processing approach:
        1. Discover all brand links from the main category page
        2. Process brands in parallel using multiple worker threads
        3. For each brand: process main page and all related category pages
        4. Aggregate all extracted part information
        
        Args:
            base_url: Base URL of the appliance category to scrape
            
        Returns:
            List of dictionaries containing comprehensive part information
        """
        all_parts_data = []
        driver = None
        
        try:
            # Initialize the primary driver for brand discovery
            self.log_extraction_progress("Initializing web browser for brand discovery...")
            driver = self.create_chrome_driver()
            
            # Stage 1: Discover all brand links from the main category page
            self.log_extraction_progress("Stage 1: Discovering brand links from main category page...")
            brand_links = self.get_brand_links(driver, base_url)
            
            # Clean up discovery driver as we'll create new ones for parallel processing
            driver.quit()
            driver = None
            
            if not brand_links:
                self.log_extraction_progress("No brand links discovered. Exiting scraping process.", "ERROR")
                return all_parts_data
            
            # Stage 2: Process brands in parallel for optimal performance
            max_workers = max(1, min(10, len(brand_links)))
            self.log_extraction_progress(f"Stage 2: Processing {len(brand_links)} brands with {max_workers} parallel workers")
            
            completed_brands = 0
            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                # Submit all brand processing tasks to the thread pool
                future_to_url = {
                    executor.submit(self.process_brand_with_exponential_backoff, url): url 
                    for url in brand_links
                }
                
                # Process completed brand tasks as they finish
                for future in as_completed(future_to_url):
                    brand_url = future_to_url[future]
                    try:
                        brand_data = future.result()
                        all_parts_data.extend(brand_data)
                        completed_brands += 1
                        self.log_extraction_progress(f"Completed brand {completed_brands}/{len(brand_links)}: {brand_url}")
                        self.log_extraction_progress(f"Discovered {len(brand_data)} parts for this brand")
                        self.log_extraction_progress(f"Overall progress: {completed_brands}/{len(brand_links)} brands processed")
                    except Exception as e:
                        self.log_extraction_progress(f"Error processing brand {brand_url}: {e}", "ERROR")
        
        except Exception as e:
            self.log_extraction_progress(f"Critical error during scraping process: {e}", "ERROR")
        
        finally:
            if driver:
                driver.quit()
        
        self.log_extraction_progress(f"Scraping process completed. Total parts discovered: {len(all_parts_data)}")
        return all_parts_data

    def export_component_data(self, parts_data, filename):
        """
        Export extracted part data to a CSV file with comprehensive error handling.
        
        Args:
            parts_data: List of dictionaries containing part information
            filename: Target CSV filename for export
        """
        if not parts_data:
            print("No data available for export.")
            return
        
        try:
            # Extract field names from the first data entry
            fieldnames = parts_data[0].keys()
            
            # Write data to CSV file with proper encoding
            with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(parts_data)
            
            print(f"Successfully exported {len(parts_data)} parts to {filename}")
        
        except Exception as e:
            print(f"Error during CSV export: {e}")

    def harvest_dishwasher_components(self):
        """
        Execute scraping process for all dishwasher parts.
        
        Returns:
            List of dictionaries containing dishwasher part information
        """
        self.log_extraction_progress("Initiating dishwasher components harvesting process...")
        parts_data = self.harvest_all_components(self.target_catalog_urls['dishwasher'])
        self.log_extraction_progress(f"Completed dishwasher harvesting. Discovered {len(parts_data)} components")
        return parts_data

    def harvest_refrigerator_components(self):
        """
        Execute scraping process for all refrigerator parts.
        
        Returns:
            List of dictionaries containing refrigerator part information
        """
        self.log_extraction_progress("Initiating refrigerator components harvesting process...")
        parts_data = self.harvest_all_components(self.target_catalog_urls['refrigerator'])
        self.log_extraction_progress(f"Completed refrigerator harvesting. Discovered {len(parts_data)} components")
        return parts_data

    def execute_complete_harvesting(self):
        """
        Execute complete scraping process for both dishwasher and refrigerator parts.
        
        This method orchestrates the entire scraping workflow and exports
        results to separate CSV files for each appliance type.
        """
        # Harvest dishwasher components
        dishwasher_components = self.harvest_dishwasher_components()
        self.export_component_data(dishwasher_components, "dishwasher_parts.csv")
        
        # Harvest refrigerator components
        refrigerator_components = self.harvest_refrigerator_components()
        self.export_component_data(refrigerator_components, "refrigerator_parts.csv")
        
        self.log_extraction_progress("Complete harvesting process finished successfully!")
        self.log_extraction_progress(f"Total dishwasher components: {len(dishwasher_components)}")
        self.log_extraction_progress(f"Total refrigerator components: {len(refrigerator_components)}")
        self.log_extraction_progress(f"Combined total: {len(dishwasher_components) + len(refrigerator_components)}")


def main():
    """
    Main execution function that creates an AppliancePartsExtractor instance
    and executes the complete harvesting process.
    """
    extractor = AppliancePartsExtractor()
    extractor.execute_complete_harvesting()


if __name__ == "__main__":
    main()
    