"""App Store scraper for iOS apps"""

import asyncio
import aiohttp
from typing import List, Dict, Any, Optional
from datetime import datetime
import json


class AppStoreScraper:
    """Scraper for iOS App Store"""
    
    BASE_URL = "https://itunes.apple.com"
    LOOKUP_URL = f"{BASE_URL}/lookup"
    SEARCH_URL = f"{BASE_URL}/search"
    
    def __init__(self):
        self.session: Optional[aiohttp.ClientSession] = None
    
    async def __aenter__(self):
        self.session = aiohttp.ClientSession(
            headers={
                "User-Agent": "AppAdvice/1.0 (Scraper; contact@appadvice.com)"
            }
        )
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
    
    async def search_apps(
        self,
        query: str,
        limit: int = 50,
        category: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Search for apps by query"""
        params = {
            "term": query,
            "media": "software",
            "entity": "software",
            "limit": limit,
        }
        
        if category:
            params["genre"] = category
        
        async with self.session.get(self.SEARCH_URL, params=params) as resp:
            data = await resp.json()
            return self._parse_search_results(data.get("results", []))
    
    async def get_app_details(self, app_id: str) -> Optional[Dict[str, Any]]:
        """Get detailed app info by ID"""
        params = {
            "id": app_id,
            "entity": "software"
        }
        
        async with self.session.get(self.LOOKUP_URL, params=params) as resp:
            data = await resp.json()
            results = data.get("results", [])
            
            if not results:
                return None
            
            return self._parse_app_data(results[0])
    
    async def get_apps_by_developer(
        self,
        developer_id: str,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """Get all apps by a developer"""
        params = {
            "id": developer_id,
            "entity": "software",
            "limit": limit
        }
        
        async with self.session.get(self.LOOKUP_URL, params=params) as resp:
            data = await resp.json()
            return self._parse_search_results(data.get("results", []))
    
    def _parse_search_results(self, results: List[Dict]) -> List[Dict[str, Any]]:
        """Parse search results"""
        return [self._parse_app_data(app) for app in results]
    
    def _parse_app_data(self, app: Dict) -> Dict[str, Any]:
        """Parse raw app data into structured format"""
        price = app.get("price", 0)
        original_price = price  # Will be updated from history
        
        return {
            "id": str(app.get("trackId")),
            "name": app.get("trackName", ""),
            "developer": app.get("artistName", ""),
            "developer_id": str(app.get("artistId", "")),
            "bundle_id": app.get("bundleId", ""),
            "category": app.get("primaryGenreName", ""),
            "sub_category": app.get("genres", [])[0] if app.get("genres") else None,
            "price": price,
            "original_price": original_price,
            "currency": app.get("currency", "USD"),
            "is_free": app.get("price", 0) == 0,
            "has_in_app_purchases": app.get("features", []) and "iosUniversal" in app.get("features", []),
            "rating": app.get("averageUserRating"),
            "rating_count": app.get("userRatingCount", 0),
            "icon_url": app.get("artworkUrl512", app.get("artworkUrl100", "")),
            "screenshots": app.get("screenshotUrls", []),
            "description": app.get("description", ""),
            "release_notes": app.get("releaseNotes"),
            "app_store_url": app.get("trackViewUrl", ""),
            "release_date": self._parse_date(app.get("releaseDate")),
            "last_updated": self._parse_date(app.get("currentVersionReleaseDate")),
            "version": app.get("version"),
            "size_bytes": app.get("fileSizeBytes"),
            "content_rating": app.get("contentAdvisoryRating"),
            "languages": app.get("languageCodesISO2A", []),
            "minimum_os_version": app.get("minimumOsVersion"),
            "supported_devices": app.get("supportedDevices", []),
        }
    
    def _parse_date(self, date_str: Optional[str]) -> Optional[datetime]:
        """Parse ISO date string"""
        if not date_str:
            return None
        try:
            return datetime.fromisoformat(date_str.replace("Z", "+00:00"))
        except:
            return None


async def scrape_popular_apps(limit: int = 200) -> List[Dict[str, Any]]:
    """Scrape popular apps across categories"""
    categories = [
        "Productivity",
        "Photo & Video",
        "Games",
        "Graphics & Design",
        "Utilities",
        "Music",
        "Health & Fitness",
        "Education",
        "Finance",
        "Travel"
    ]
    
    all_apps = []
    
    async with AppStoreScraper() as scraper:
        # Scrape each category
        for category in categories:
            try:
                apps = await scraper.search_apps(
                    query=category,
                    limit=limit // len(categories),
                    category=category
                )
                all_apps.extend(apps)
                await asyncio.sleep(0.5)  # Rate limiting
            except Exception as e:
                print(f"Error scraping {category}: {e}")
    
    # Deduplicate by ID
    seen_ids = set()
    unique_apps = []
    for app in all_apps:
        if app["id"] not in seen_ids:
            seen_ids.add(app["id"])
            unique_apps.append(app)
    
    return unique_apps


async def update_app_prices(app_ids: List[str]) -> List[Dict[str, Any]]:
    """Update prices for specific apps"""
    updates = []
    
    async with AppStoreScraper() as scraper:
        for app_id in app_ids:
            try:
                app_data = await scraper.get_app_details(app_id)
                if app_data:
                    updates.append(app_data)
                await asyncio.sleep(0.2)  # Rate limiting
            except Exception as e:
                print(f"Error updating {app_id}: {e}")
    
    return updates
