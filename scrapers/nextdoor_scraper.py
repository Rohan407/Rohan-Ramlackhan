import asyncio
import re
from typing import List, Dict, Optional
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from bs4 import BeautifulSoup
import pandas as pd
from datetime import datetime, timedelta
import logging
from config.settings import settings


class NextdoorScraper:
    """Scraper for finding storm-related posts on Nextdoor"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.driver = None
        self.storm_keywords = [
            "roof damage", "storm damage", "hail damage", "wind damage",
            "tree on roof", "roof leak", "shingles blown off",
            "roofing contractor", "roof repair", "insurance claim",
            "roofer recommendation", "roof inspection"
        ]
        
    def setup_driver(self):
        """Setup Chrome WebDriver with appropriate options"""
        chrome_options = Options()
        chrome_options.add_argument("--headless")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-blink-features=AutomationControlled")
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option('useAutomationExtension', False)
        
        self.driver = webdriver.Chrome(options=chrome_options)
        self.driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
    
    async def search_by_location(self, location: str, zip_code: str = None) -> List[Dict]:
        """Search Nextdoor posts by location"""
        posts = []
        
        try:
            # Navigate to Nextdoor
            self.driver.get("https://nextdoor.com")
            await asyncio.sleep(3)
            
            # If zip code provided, use it to set location
            if zip_code:
                await self._set_location(zip_code)
            
            # Search for storm-related posts
            for keyword in self.storm_keywords:
                search_posts = await self._search_keyword(keyword, location)
                posts.extend(search_posts)
                await asyncio.sleep(2)  # Rate limiting
                
        except Exception as e:
            self.logger.error(f"Error searching Nextdoor by location: {e}")
            
        return posts
    
    async def _set_location(self, zip_code: str):
        """Set the location on Nextdoor"""
        try:
            # Look for location input or zip code field
            location_input = WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "input[placeholder*='zip']"))
            )
            location_input.clear()
            location_input.send_keys(zip_code)
            
            # Submit or click search
            submit_button = self.driver.find_element(By.CSS_SELECTOR, "button[type='submit']")
            submit_button.click()
            
            await asyncio.sleep(3)
            
        except Exception as e:
            self.logger.warning(f"Could not set location: {e}")
    
    async def _search_keyword(self, keyword: str, location: str) -> List[Dict]:
        """Search for a specific keyword on Nextdoor"""
        posts = []
        
        try:
            # Nextdoor search URL format
            search_url = f"https://nextdoor.com/search/?query={keyword.replace(' ', '+')}"
            self.driver.get(search_url)
            await asyncio.sleep(3)
            
            # Scroll to load more content
            for _ in range(3):
                self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                await asyncio.sleep(2)
            
            soup = BeautifulSoup(self.driver.page_source, 'html.parser')
            
            # Extract posts (Nextdoor structure may vary)
            post_elements = self._find_post_elements(soup)
            
            for element in post_elements:
                post_data = self._extract_nextdoor_post(element, keyword, location)
                if post_data:
                    posts.append(post_data)
                    
        except Exception as e:
            self.logger.error(f"Error searching keyword '{keyword}': {e}")
            
        return posts
    
    def _find_post_elements(self, soup: BeautifulSoup) -> List:
        """Find post elements in Nextdoor HTML structure"""
        # Multiple selectors as Nextdoor structure may vary
        selectors = [
            'div[data-testid="post"]',
            'article',
            'div[class*="post"]',
            'div[class*="feed-item"]'
        ]
        
        post_elements = []
        for selector in selectors:
            elements = soup.select(selector)
            if elements:
                post_elements.extend(elements)
                break
                
        return post_elements
    
    def _extract_nextdoor_post(self, element, search_keyword: str, location: str) -> Optional[Dict]:
        """Extract post information from Nextdoor HTML element"""
        try:
            # Extract text content
            text_content = element.get_text(strip=True)
            
            if len(text_content) < 20:
                return None
            
            # Extract author (if available)
            author_selectors = [
                'span[class*="author"]',
                'div[class*="user-name"]',
                'a[class*="profile"]'
            ]
            
            author_name = "Anonymous"
            for selector in author_selectors:
                author_elem = element.select_one(selector)
                if author_elem:
                    author_name = author_elem.get_text(strip=True)
                    break
            
            # Extract neighborhood (if available)
            neighborhood_selectors = [
                'span[class*="neighborhood"]',
                'div[class*="location"]'
            ]
            
            neighborhood = location
            for selector in neighborhood_selectors:
                neighborhood_elem = element.select_one(selector)
                if neighborhood_elem:
                    neighborhood = neighborhood_elem.get_text(strip=True)
                    break
            
            return {
                'author': author_name,
                'content': text_content,
                'neighborhood': neighborhood,
                'search_keyword': search_keyword,
                'platform': 'nextdoor',
                'timestamp': datetime.now().isoformat(),
                'potential_lead': self._analyze_nextdoor_lead(text_content),
                'scraped_at': datetime.now().isoformat()
            }
            
        except Exception as e:
            self.logger.debug(f"Error extracting Nextdoor post: {e}")
            return None
    
    def _analyze_nextdoor_lead(self, text: str) -> Dict:
        """Analyze Nextdoor post for lead potential"""
        text_lower = text.lower()
        
        # Nextdoor-specific indicators
        request_indicators = ["looking for", "need", "recommend", "anyone know"]
        urgency_indicators = ["urgent", "emergency", "asap", "quickly"]
        damage_indicators = ["damage", "leak", "broken", "repair", "fix"]
        recommendation_indicators = ["recommend", "suggestion", "advice", "referral"]
        
        request_score = sum(1 for phrase in request_indicators if phrase in text_lower)
        urgency_score = sum(1 for word in urgency_indicators if word in text_lower)
        damage_score = sum(1 for word in damage_indicators if word in text_lower)
        recommendation_score = sum(1 for word in recommendation_indicators if word in text_lower)
        
        # Nextdoor posts asking for recommendations are high value
        total_score = (request_score * 3 + urgency_score * 2 + 
                      damage_score * 2 + recommendation_score * 4)
        
        if total_score >= 6:
            priority = "high"
        elif total_score >= 3:
            priority = "medium"
        else:
            priority = "low"
            
        return {
            'priority': priority,
            'request_score': request_score,
            'urgency_score': urgency_score,
            'damage_score': damage_score,
            'recommendation_score': recommendation_score,
            'total_score': total_score
        }
    
    async def scrape_neighborhood_posts(self, zip_codes: List[str]) -> List[Dict]:
        """Scrape posts from multiple neighborhoods"""
        all_posts = []
        
        for zip_code in zip_codes:
            try:
                self.logger.info(f"Scraping posts for zip code: {zip_code}")
                posts = await self.search_by_location(f"zip {zip_code}", zip_code)
                all_posts.extend(posts)
                
                # Add delay between zip codes to avoid rate limiting
                await asyncio.sleep(5)
                
            except Exception as e:
                self.logger.error(f"Error scraping zip code {zip_code}: {e}")
                continue
                
        return all_posts
    
    async def scrape_recent_activity(self, location: str, days_back: int = 7) -> List[Dict]:
        """Scrape recent activity in the area"""
        posts = []
        
        try:
            # Navigate to recent activity or feed
            activity_url = "https://nextdoor.com/news_feed/"
            self.driver.get(activity_url)
            await asyncio.sleep(3)
            
            # Scroll through recent posts
            for _ in range(5):
                self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                await asyncio.sleep(2)
            
            soup = BeautifulSoup(self.driver.page_source, 'html.parser')
            post_elements = self._find_post_elements(soup)
            
            for element in post_elements:
                post_text = element.get_text(strip=True).lower()
                
                # Check if post contains storm/roof keywords
                if any(keyword.lower() in post_text for keyword in self.storm_keywords):
                    post_data = self._extract_nextdoor_post(element, "recent_activity", location)
                    if post_data:
                        posts.append(post_data)
                        
        except Exception as e:
            self.logger.error(f"Error scraping recent activity: {e}")
            
        return posts
    
    def close(self):
        """Close the WebDriver"""
        if self.driver:
            self.driver.quit()
    
    async def __aenter__(self):
        self.setup_driver()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        self.close()


# Utility functions
async def scrape_nextdoor_leads(zip_codes: List[str], location: str = None) -> pd.DataFrame:
    """Main function to scrape Nextdoor for roofing leads"""
    async with NextdoorScraper() as scraper:
        # Scrape by zip codes
        posts = await scraper.scrape_neighborhood_posts(zip_codes)
        
        # Also scrape recent activity if location provided
        if location:
            recent_posts = await scraper.scrape_recent_activity(location)
            posts.extend(recent_posts)
        
        if posts:
            df = pd.DataFrame(posts)
            # Remove duplicates
            df = df.drop_duplicates(subset=['content'], keep='first')
            # Sort by lead potential
            priority_map = {'high': 3, 'medium': 2, 'low': 1}
            df['priority_score'] = df['potential_lead'].apply(lambda x: priority_map.get(x.get('priority', 'low'), 1))
            df = df.sort_values('priority_score', ascending=False)
            return df
        else:
            return pd.DataFrame()


def get_storm_affected_zip_codes(storm_location: str, radius_miles: int = 25) -> List[str]:
    """Get zip codes in the area affected by storm"""
    # This is a simplified version - in practice, you'd use weather APIs
    # or news sources to identify actually affected areas
    
    # Example zip codes for common storm-prone areas
    storm_zip_maps = {
        "miami": ["33101", "33102", "33125", "33126", "33127", "33128", "33129", "33130"],
        "houston": ["77001", "77002", "77003", "77004", "77005", "77006", "77007", "77008"],
        "orlando": ["32801", "32802", "32803", "32804", "32805", "32806", "32807", "32808"],
        "tampa": ["33601", "33602", "33603", "33604", "33605", "33606", "33607", "33608"]
    }
    
    location_key = storm_location.lower().split(',')[0].strip()
    return storm_zip_maps.get(location_key, ["12345"])  # Default fallback


if __name__ == "__main__":
    # Test the scraper
    async def main():
        zip_codes = get_storm_affected_zip_codes("Miami, FL")
        results = await scrape_nextdoor_leads(zip_codes, "Miami, FL")
        print(f"Found {len(results)} potential leads from Nextdoor")
        if len(results) > 0:
            print(results.head())
    
    asyncio.run(main())