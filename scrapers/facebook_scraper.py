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


class FacebookScraper:
    """Scraper for finding storm-related posts and homeowners on Facebook"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.driver = None
        self.storm_keywords = [
            "roof damage", "storm damage", "hail damage", "wind damage",
            "tree fell on roof", "roof leak", "missing shingles",
            "roof repair needed", "insurance claim", "roofing contractor needed"
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
        
    async def login(self) -> bool:
        """Login to Facebook if credentials are provided"""
        if not settings.facebook_email or not settings.facebook_password:
            self.logger.warning("Facebook credentials not provided. Limited access only.")
            return False
            
        try:
            self.driver.get("https://www.facebook.com/login")
            
            email_field = WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.ID, "email"))
            )
            password_field = self.driver.find_element(By.ID, "pass")
            
            email_field.send_keys(settings.facebook_email)
            password_field.send_keys(settings.facebook_password)
            
            login_button = self.driver.find_element(By.NAME, "login")
            login_button.click()
            
            # Wait for successful login
            WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "[data-testid='app_section']"))
            )
            
            self.logger.info("Successfully logged into Facebook")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to login to Facebook: {e}")
            return False
    
    async def search_local_groups(self, location: str, radius_miles: int = 25) -> List[Dict]:
        """Search for local Facebook groups in the area"""
        groups = []
        try:
            search_terms = [
                f"{location} community",
                f"{location} neighbors",
                f"{location} residents",
                f"{location} storm damage",
                f"{location} roof repair"
            ]
            
            for term in search_terms:
                search_url = f"https://www.facebook.com/search/groups/?q={term.replace(' ', '%20')}"
                self.driver.get(search_url)
                
                await asyncio.sleep(3)  # Wait for page load
                
                # Extract group information
                soup = BeautifulSoup(self.driver.page_source, 'html.parser')
                group_elements = soup.find_all('div', {'role': 'article'})
                
                for element in group_elements[:5]:  # Limit to top 5 groups per search
                    group_info = self._extract_group_info(element)
                    if group_info:
                        groups.append(group_info)
                        
        except Exception as e:
            self.logger.error(f"Error searching local groups: {e}")
            
        return groups
    
    async def scrape_storm_posts(self, location: str, days_back: int = 30) -> List[Dict]:
        """Scrape posts related to storm damage in the specified location"""
        posts = []
        
        try:
            for keyword in self.storm_keywords:
                search_query = f"{keyword} {location}"
                search_url = f"https://www.facebook.com/search/posts/?q={search_query.replace(' ', '%20')}"
                
                self.driver.get(search_url)
                await asyncio.sleep(3)
                
                # Scroll to load more posts
                for _ in range(3):
                    self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                    await asyncio.sleep(2)
                
                soup = BeautifulSoup(self.driver.page_source, 'html.parser')
                post_elements = soup.find_all('div', {'role': 'article'})
                
                for element in post_elements:
                    post_data = self._extract_post_info(element, keyword)
                    if post_data and self._is_recent_post(post_data['timestamp'], days_back):
                        posts.append(post_data)
                        
        except Exception as e:
            self.logger.error(f"Error scraping storm posts: {e}")
            
        return posts
    
    def _extract_group_info(self, element) -> Optional[Dict]:
        """Extract group information from HTML element"""
        try:
            group_name = element.find('span', {'dir': 'auto'})
            if not group_name:
                return None
                
            return {
                'name': group_name.get_text(strip=True),
                'type': 'facebook_group',
                'scraped_at': datetime.now().isoformat()
            }
        except Exception:
            return None
    
    def _extract_post_info(self, element, search_keyword: str) -> Optional[Dict]:
        """Extract post information from HTML element"""
        try:
            # Extract post text
            text_elements = element.find_all('div', {'data-ad-preview': 'message'})
            if not text_elements:
                text_elements = element.find_all('div', {'dir': 'auto'})
            
            post_text = ""
            for text_elem in text_elements:
                post_text += text_elem.get_text(strip=True) + " "
            
            if not post_text or len(post_text) < 20:
                return None
            
            # Extract author information
            author_elements = element.find_all('strong', {'dir': 'auto'})
            author_name = author_elements[0].get_text(strip=True) if author_elements else "Unknown"
            
            # Extract timestamp (simplified)
            time_elements = element.find_all('a', {'role': 'link'})
            timestamp = datetime.now().isoformat()  # Fallback to current time
            
            return {
                'author': author_name,
                'content': post_text.strip(),
                'timestamp': timestamp,
                'search_keyword': search_keyword,
                'platform': 'facebook',
                'potential_lead': self._analyze_lead_potential(post_text),
                'scraped_at': datetime.now().isoformat()
            }
            
        except Exception as e:
            self.logger.debug(f"Error extracting post info: {e}")
            return None
    
    def _analyze_lead_potential(self, text: str) -> Dict:
        """Analyze the text to determine lead potential"""
        text_lower = text.lower()
        
        urgency_indicators = ["urgent", "emergency", "asap", "immediately", "help"]
        damage_indicators = ["leak", "hole", "missing", "damaged", "broken", "destroyed"]
        insurance_indicators = ["insurance", "claim", "adjuster", "coverage"]
        
        urgency_score = sum(1 for word in urgency_indicators if word in text_lower)
        damage_score = sum(1 for word in damage_indicators if word in text_lower)
        insurance_score = sum(1 for word in insurance_indicators if word in text_lower)
        
        total_score = urgency_score * 3 + damage_score * 2 + insurance_score * 1
        
        if total_score >= 5:
            priority = "high"
        elif total_score >= 3:
            priority = "medium"
        else:
            priority = "low"
            
        return {
            'priority': priority,
            'urgency_score': urgency_score,
            'damage_score': damage_score,
            'insurance_score': insurance_score,
            'total_score': total_score
        }
    
    def _is_recent_post(self, timestamp: str, days_back: int) -> bool:
        """Check if post is within the specified timeframe"""
        try:
            post_date = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
            cutoff_date = datetime.now() - timedelta(days=days_back)
            return post_date >= cutoff_date
        except Exception:
            return True  # If we can't parse the date, include the post
    
    async def scrape_public_posts_by_location(self, location: str) -> List[Dict]:
        """Scrape public posts from location-based searches"""
        all_posts = []
        
        try:
            # Search for recent posts in the location
            posts = await self.scrape_storm_posts(location)
            all_posts.extend(posts)
            
            # Search local groups
            groups = await self.search_local_groups(location)
            self.logger.info(f"Found {len(groups)} local groups for {location}")
            
        except Exception as e:
            self.logger.error(f"Error in location-based scraping: {e}")
            
        return all_posts
    
    def close(self):
        """Close the WebDriver"""
        if self.driver:
            self.driver.quit()
    
    async def __aenter__(self):
        self.setup_driver()
        await self.login()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        self.close()


# Usage example and utility functions
async def scrape_facebook_leads(location: str, days_back: int = 30) -> pd.DataFrame:
    """Main function to scrape Facebook for potential roofing leads"""
    async with FacebookScraper() as scraper:
        posts = await scraper.scrape_public_posts_by_location(location)
        
        if posts:
            df = pd.DataFrame(posts)
            # Sort by lead potential
            df = df.sort_values('potential_lead', key=lambda x: x.map({'high': 3, 'medium': 2, 'low': 1}), ascending=False)
            return df
        else:
            return pd.DataFrame()


if __name__ == "__main__":
    # Test the scraper
    async def main():
        location = "Miami, FL"  # Example location
        results = await scrape_facebook_leads(location)
        print(f"Found {len(results)} potential leads")
        if len(results) > 0:
            print(results.head())
    
    asyncio.run(main())