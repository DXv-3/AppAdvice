"""Google Play Store scraper for Android apps

This scraper fetches app data from Google Play Store to provide
Android app discovery alongside iOS apps.
"""

import asyncio
import json
import re
from typing import List, Dict, Optional, Any
from dataclasses import dataclass
from datetime import datetime

import aiohttp
from bs4 import BeautifulSoup


@dataclass
class GooglePlayApp:
    """Represents a Google Play Store app"""
    id: str
    name: str
    developer: str
    category: str
    price: float
    original_price: float
    is_free: bool
    rating: float
    rating_count: int
    description: str
    icon_url: str
    screenshots: List[str]
    install_count: str
    content_rating: str
    last_updated: str
    app_store_url: str


class GooglePlayScraper:
    """Scraper for Google Play Store"""
    
    BASE_URL = "https://play.google.com"
    
    # Category IDs for Google Play
    CATEGORIES = {
        "PRODUCTIVITY": "PRODUCTIVITY",
        "PHOTOGRAPHY": "PHOTOGRAPHY",
        "HEALTH_AND_FITNESS": "HEALTH_AND_FITNESS",
        "FINANCE": "FINANCE",
        "EDUCATION": "EDUCATION",
        "ENTERTAINMENT": "ENTERTAINMENT",
        "MUSIC_AND_AUDIO": "MUSIC_AND_AUDIO",
        "TRAVEL_AND_LOCAL": "TRAVEL_AND_LOCAL",
        "SOCIAL": "SOCIAL",
        "COMMUNICATION": "COMMUNICATION",
        "SHOPPING": "SHOPPING",
        "SPORTS": "SPORTS",
        "NEWS_AND_MAGAZINES": "NEWS_AND_MAGAZINES",
        "BOOKS_AND_REFERENCE": "BOOKS_AND_REFERENCE",
        "LIFESTYLE": "LIFESTYLE",
        "FOOD_AND_DRINK": "FOOD_AND_DRINK",
        "GAME_ACTION": "GAME_ACTION",
        "GAME_ADVENTURE": "GAME_ADVENTURE",
        "GAME_ARCADE": "GAME_ARCADE",
        "GAME_BOARD": "GAME_BOARD",
        "GAME_CARD": "GAME_CARD",
        "GAME_CASINO": "GAME_CASINO",
        "GAME_CASUAL": "GAME_CASUAL",
        "GAME_EDUCATIONAL": "GAME_EDUCATIONAL",
        "GAME_MUSIC": "GAME_MUSIC",
        "GAME_PUZZLE": "GAME_PUZZLE",
        "GAME_RACING": "GAME_RACING",
        "GAME_ROLE_PLAYING": "GAME_ROLE_PLAYING",
        "GAME_SIMULATION": "GAME_SIMULATION",
        "GAME_SPORTS": "GAME_SPORTS",
        "GAME_STRATEGY": "GAME_STRATEGY",
        "GAME_TRIVIA": "GAME_TRIVIA",
        "GAME_WORD": "GAME_WORD",
    }
    
    def __init__(self):
        self.session: Optional[aiohttp.ClientSession] = None
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept-Language": "en-US,en;q=0.9",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        }
    
    async def __aenter__(self):
        self.session = aiohttp.ClientSession(headers=self.headers)
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
    
    async def _fetch(self, url: str) -> Optional[str]:
        """Fetch URL content"""
        if not self.session:
            self.session = aiohttp.ClientSession(headers=self.headers)
        
        try:
            async with self.session.get(url, timeout=aiohttp.ClientTimeout(total=30)) as response:
                if response.status == 200:
                    return await response.text()
                print(f"Failed to fetch {url}: {response.status}")
                return None
        except Exception as e:
            print(f"Error fetching {url}: {e}")
            return None
    
    def _parse_price(self, price_text: str) -> tuple[float, bool]:
        """Parse price from text, returns (price, is_free)"""
        if not price_text or price_text.lower() in ["free", "install"]:
            return 0.0, True
        
        # Extract numeric price
        match = re.search(r'[\d,]+\.?\d*', price_text.replace(",", ""))
        if match:
            try:
                price = float(match.group())
                return price, False
            except ValueError:
                pass
        
        return 0.0, True
    
    def _extract_rating(self, rating_text: str) -> float:
        """Extract rating from text"""
        if not rating_text:
            return 0.0
        
        match = re.search(r'(\d+\.?\d*)', rating_text)
        if match:
            try:
                return float(match.group(1))
            except ValueError:
                pass
        
        return 0.0
    
    async def get_app_details(self, package_name: str) -> Optional[GooglePlayApp]:
        """Get detailed information about a specific app"""
        
        url = f"{self.BASE_URL}/store/apps/details?id={package_name}"
        html = await self._fetch(url)
        
        if not html:
            return None
        
        soup = BeautifulSoup(html, 'html.parser')
        
        try:
            # Extract app name
            name_elem = soup.find('h1')
            name = name_elem.text.strip() if name_elem else package_name
            
            # Extract developer
            dev_elem = soup.find('div', string=re.compile('Offered by'))
            developer = "Unknown"
            if dev_elem:
                dev_text = dev_elem.text
                match = re.search(r'Offered by\s+(.+)', dev_text)
                if match:
                    developer = match.group(1).strip()
            
            # Extract category
            category = "Unknown"
            category_link = soup.find('a', href=re.compile(r'/store/apps/category/'))
            if category_link:
                category = category_link.text.strip()
            
            # Extract price
            price_elem = soup.find('span', string=re.compile(r'\$|Free|Install'))
            price_text = price_elem.text if price_elem else "Free"
            price, is_free = self._parse_price(price_text)
            
            # Extract rating
            rating_elem = soup.find('div', {'role': 'img'})
            rating = 0.0
            rating_count = 0
            if rating_elem:
                rating_text = rating_elem.get('aria-label', '')
                rating = self._extract_rating(rating_text)
                # Try to find rating count
                count_match = re.search(r'(\d+(?:,\d+)*)\s+reviews?', rating_text)
                if count_match:
                    rating_count = int(count_match.group(1).replace(",", ""))
            
            # Extract description
            desc_elem = soup.find('div', {'data-g-id': 'description'})
            description = ""
            if desc_elem:
                description = desc_elem.get_text(separator=' ', strip=True)
            
            # Extract icon
            icon_elem = soup.find('img', {'alt': 'Icon image'})
            icon_url = ""
            if icon_elem:
                icon_url = icon_elem.get('src', '')
            
            # Extract screenshots
            screenshots = []
            screenshot_elems = soup.find_all('img', {'alt': re.compile(r'Screenshot')})
            for elem in screenshot_elems[:5]:  # Limit to 5 screenshots
                src = elem.get('src', '')
                if src:
                    screenshots.append(src)
            
            # Extract install count
            install_elem = soup.find('div', string=re.compile(r'\d+\+\s+downloads?'))
            install_count = "Unknown"
            if install_elem:
                install_count = install_elem.text.strip()
            
            # Extract content rating
            content_rating = "Everyone"
            rating_elem = soup.find('div', string=re.compile(r'Rated\s+\d+\+'))
            if rating_elem:
                content_rating = rating_elem.text.strip()
            
            # Extract last updated
            updated_elem = soup.find('div', string=re.compile(r'Updated on'))
            last_updated = datetime.now().isoformat()
            if updated_elem:
                updated_text = updated_elem.text
                match = re.search(r'Updated on\s+(.+)', updated_text)
                if match:
                    last_updated = match.group(1).strip()
            
            return GooglePlayApp(
                id=package_name,
                name=name,
                developer=developer,
                category=category,
                price=price,
                original_price=price,  # Will be updated when we track history
                is_free=is_free,
                rating=rating,
                rating_count=rating_count,
                description=description[:500],  # Limit description length
                icon_url=icon_url,
                screenshots=screenshots,
                install_count=install_count,
                content_rating=content_rating,
                last_updated=last_updated,
                app_store_url=url
            )
            
        except Exception as e:
            print(f"Error parsing app details for {package_name}: {e}")
            return None
    
    async def get_top_charts(self, category: str = "PRODUCTIVITY", collection: str = "topselling_free") -> List[GooglePlayApp]:
        """Get top apps from a category"""
        
        url = f"{self.BASE_URL}/store/apps/collection/cluster?clp={collection}:{category}:PRODUCTIVITY&gsr={collection}:{category}"
        
        # Alternative: Use the browse URL
        browse_url = f"{self.BASE_URL}/store/apps/category/{category}"
        
        html = await self._fetch(browse_url)
        
        if not html:
            return []
        
        apps = []
        soup = BeautifulSoup(html, 'html.parser')
        
        # Find app links
        app_links = soup.find_all('a', href=re.compile(r'/store/apps/details\?id='))
        
        # Extract package names
        package_names = []
        for link in app_links[:20]:  # Limit to 20 apps
            href = link.get('href', '')
            match = re.search(r'id=([\w\.]+)', href)
            if match:
                package_name = match.group(1)
                if package_name not in package_names:
                    package_names.append(package_name)
        
        # Fetch details for each app
        for package_name in package_names[:10]:  # Limit to 10 for performance
            app = await self.get_app_details(package_name)
            if app:
                apps.append(app)
            await asyncio.sleep(0.5)  # Be nice to Google servers
        
        return apps
    
    async def search_apps(self, query: str, limit: int = 10) -> List[GooglePlayApp]:
        """Search for apps on Google Play"""
        
        # Google Play search URL
        search_url = f"{self.BASE_URL}/store/search?q={query.replace(' ', '+')}&c=apps"
        
        html = await self._fetch(search_url)
        
        if not html:
            return []
        
        apps = []
        soup = BeautifulSoup(html, 'html.parser')
        
        # Find app links in search results
        app_links = soup.find_all('a', href=re.compile(r'/store/apps/details\?id='))
        
        package_names = []
        for link in app_links[:limit * 2]:  # Get extra for filtering
            href = link.get('href', '')
            match = re.search(r'id=([\w\.]+)', href)
            if match:
                package_name = match.group(1)
                if package_name not in package_names:
                    package_names.append(package_name)
        
        # Fetch details
        for package_name in package_names[:limit]:
            app = await self.get_app_details(package_name)
            if app:
                apps.append(app)
            await asyncio.sleep(0.3)
        
        return apps
    
    async def get_deals(self, min_discount_percent: float = 50.0) -> List[GooglePlayApp]:
        """Get apps with significant discounts"""
        
        # This is a simplified implementation
        # In production, you'd need to track price history to detect discounts
        
        deals = []
        
        # Check paid apps category for sales
        paid_apps = await self.get_top_charts(collection="topselling_paid", limit=50)
        
        for app in paid_apps:
            # For now, we can't detect discounts without historical data
            # This would require a database to track price changes
            pass
        
        return deals


# Convenience functions for use in other modules

async def scrape_android_app(package_name: str) -> Optional[Dict[str, Any]]:
    """Scrape a single Android app by package name"""
    async with GooglePlayScraper() as scraper:
        app = await scraper.get_app_details(package_name)
        if app:
            return {
                "id": app.id,
                "name": app.name,
                "developer": app.developer,
                "category": app.category,
                "price": app.price,
                "original_price": app.original_price,
                "is_free": app.is_free,
                "rating": app.rating,
                "rating_count": app.rating_count,
                "description": app.description,
                "icon_url": app.icon_url,
                "screenshots": app.screenshots,
                "platform": "android",
                "install_count": app.install_count,
                "content_rating": app.content_rating,
                "last_updated": app.last_updated,
                "app_store_url": app.app_store_url,
            }
        return None


async def search_android_apps(query: str, limit: int = 10) -> List[Dict[str, Any]]:
    """Search for Android apps"""
    async with GooglePlayScraper() as scraper:
        apps = await scraper.search_apps(query, limit)
        return [
            {
                "id": app.id,
                "name": app.name,
                "developer": app.developer,
                "category": app.category,
                "price": app.price,
                "is_free": app.is_free,
                "rating": app.rating,
                "icon_url": app.icon_url,
                "platform": "android",
                "app_store_url": app.app_store_url,
            }
            for app in apps
        ]


# For testing
if __name__ == "__main__":
    async def test():
        # Test scraping a popular app
        result = await scrape_android_app("com.whatsapp")
        if result:
            print(f"✅ Found: {result['name']} by {result['developer']}")
            print(f"   Rating: {result['rating']}")
            print(f"   Price: {'Free' if result['is_free'] else '$' + str(result['price'])}")
        else:
            print("❌ Could not fetch app details")
        
        # Test search
        print("\n🔍 Searching for 'photo editor':")
        results = await search_android_apps("photo editor", limit=3)
        for app in results:
            print(f"  - {app['name']} ({app['rating']}★)")
    
    asyncio.run(test())
