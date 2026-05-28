"""
Google Search Module
Handles actual Google search queries
"""

import requests
from urllib.parse import quote
import time
from typing import List, Dict
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class GoogleSearcher:
    """Handle Google searches for dorking queries"""
    
    def __init__(self, delay: float = 1.0):
        """
        Initialize GoogleSearcher
        
        Args:
            delay: Delay between requests in seconds (to avoid rate limiting)
        """
        self.delay = delay
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
        self.total_queries = 0
        self.successful_queries = 0
        self.failed_queries = 0
    
    def search(self, query: str, max_results: int = 10) -> Dict:
        """
        Perform a Google search query
        
        Args:
            query: The search query string
            max_results: Maximum number of results to return
        
        Returns:
            Dictionary containing results or error info
        """
        self.total_queries += 1
        
        try:
            # Using Google Custom Search API format (you can use SerpAPI as well)
            # This is a basic implementation that constructs a Google search URL
            encoded_query = quote(query)
            search_url = f"https://www.google.com/search?q={encoded_query}"
            
            response = self.session.get(search_url, timeout=10)
            response.raise_for_status()
            
            self.successful_queries += 1
            
            return {
                "status": "success",
                "query": query,
                "url": search_url,
                "status_code": response.status_code,
                "content_length": len(response.content),
                "results": self._parse_results(response.text, max_results)
            }
        
        except requests.RequestException as e:
            self.failed_queries += 1
            logger.error(f"Error searching for '{query}': {str(e)}")
            return {
                "status": "error",
                "query": query,
                "error": str(e)
            }
        finally:
            time.sleep(self.delay)
    
    def search_batch(self, queries: List[str], max_results: int = 10) -> List[Dict]:
        """
        Perform multiple searches
        
        Args:
            queries: List of search queries
            max_results: Max results per query
        
        Returns:
            List of search results
        """
        results = []
        for query in queries:
            result = self.search(query, max_results)
            results.append(result)
        
        return results
    
    def _parse_results(self, html: str, max_results: int) -> List[Dict]:
        """
        Parse HTML response for results
        
        Args:
            html: HTML content from search
            max_results: Max results to extract
        
        Returns:
            List of result dictionaries
        """
        try:
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(html, 'lxml')
            
            results = []
            search_results = soup.find_all('div', {'class': 'g'})[:max_results]
            
            for result in search_results:
                try:
                    title_elem = result.find('h3')
                    link_elem = result.find('a')
                    desc_elem = result.find('span', {'class': 'st'})
                    
                    if title_elem and link_elem:
                        results.append({
                            'title': title_elem.get_text(),
                            'url': link_elem.get('href', ''),
                            'description': desc_elem.get_text() if desc_elem else ''
                        })
                except Exception as e:
                    logger.warning(f"Error parsing individual result: {e}")
                    continue
            
            return results
        except Exception as e:
            logger.error(f"Error parsing results: {e}")
            return []
    
    def get_stats(self) -> Dict:
        """Get search statistics"""
        return {
            "total_queries": self.total_queries,
            "successful_queries": self.successful_queries,
            "failed_queries": self.failed_queries,
            "success_rate": (self.successful_queries / self.total_queries * 100) if self.total_queries > 0 else 0
        }
