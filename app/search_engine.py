"""
Google Search Module
Uses googlesearch-python library (no API key needed) as primary,
falls back to raw requests + bs4 parsing.
Conservative rate limiting to avoid 429s.
"""

import time
import threading
import logging
from urllib.parse import quote, unquote
from typing import List, Dict

import requests

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Check optional deps once at import
try:
    from googlesearch import search as gsearch
    GSEARCH_AVAILABLE = True
    logger.info("googlesearch-python available — using as primary search engine")
except ImportError:
    GSEARCH_AVAILABLE = False
    logger.warning("googlesearch-python not installed. Run: pip install googlesearch-python")

try:
    from bs4 import BeautifulSoup
    BS4_AVAILABLE = True
    try:
        import lxml as _lxml  # noqa: F401
        BS4_PARSER = 'lxml'
    except ImportError:
        BS4_PARSER = 'html.parser'
except ImportError:
    BS4_AVAILABLE = False
    BS4_PARSER = 'html.parser'
    logger.warning("beautifulsoup4 not installed. Run: pip install beautifulsoup4")


class RateLimiter:
    """Thread-safe token-bucket rate limiter."""
    def __init__(self, rate: float = 0.5):
        self.min_interval = 1.0 / rate
        self._lock = threading.Lock()
        self._last_call = 0.0

    def acquire(self):
        with self._lock:
            now = time.monotonic()
            wait = self._last_call + self.min_interval - now
            if wait > 0:
                time.sleep(wait)
            self._last_call = time.monotonic()


class GoogleSearcher:
    """
    Thread-safe Google dorking searcher.

    Priority:
      1. googlesearch-python  (handles throttling internally, most reliable)
      2. Raw requests + bs4   (fallback, may get blocked)

    Never returns the dork query URL itself as a "finding".
    """

    def __init__(self, delay: float = 2.0, rate_limit: float = 0.5):
        self.delay = delay
        self.rate_limiter = RateLimiter(rate=rate_limit)
        self._thread_local = threading.local()
        self._lock = threading.Lock()
        self.total_queries = 0
        self.successful_queries = 0
        self.failed_queries = 0
        self._consecutive_429s = 0

    # ── session ──────────────────────────────────────────────────────────

    def _get_session(self) -> requests.Session:
        if not hasattr(self._thread_local, 'session'):
            s = requests.Session()
            s.headers.update({
                'User-Agent': (
                    'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 '
                    '(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36'
                ),
                'Accept-Language': 'en-US,en;q=0.9',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            })
            self._thread_local.session = s
        return self._thread_local.session

    # ── stats ─────────────────────────────────────────────────────────────

    def _inc(self, success: bool):
        with self._lock:
            self.total_queries += 1
            if success:
                self.successful_queries += 1
                self._consecutive_429s = 0
            else:
                self.failed_queries += 1

    # ── main search ───────────────────────────────────────────────────────

    def search(self, query: str, max_results: int = 5) -> Dict:
        """
        Run one dork query. Returns structured result dict.
        The Google search URL is stored in result['url'] for manual use
        but is NEVER included in result['results'] as a finding.
        """
        with self._lock:
            consec = self._consecutive_429s
        if consec >= 3:
            extra = min(consec * 5, 60)
            logger.warning(f"Back-off extra {extra}s after {consec} consecutive 429s")
            time.sleep(extra)

        self.rate_limiter.acquire()

        encoded    = quote(query)
        search_url = f"https://www.google.com/search?q={encoded}&num={max_results}&hl=en"

        # Try googlesearch-python first
        if GSEARCH_AVAILABLE:
            result = self._search_via_library(query, max_results, search_url)
        else:
            result = self._search_via_requests(query, max_results, search_url)

        if self.delay > 0:
            time.sleep(self.delay)

        return result

    # ── googlesearch-python backend ───────────────────────────────────────

    def _search_via_library(self, query: str, max_results: int, search_url: str) -> Dict:
        try:
            urls = list(gsearch(query, num_results=max_results, sleep_interval=2, lang="en"))
            results = []
            for url in urls:
                # Filter out google.com URLs (redirects, cache links etc.)
                if 'google.com' in url:
                    continue
                results.append({
                    'title': self._url_to_title(url),
                    'url': url,
                    'description': '',
                })

            self._inc(success=True)
            return {
                'status': 'success',
                'query': query,
                'url': search_url,
                'blocked': False,
                'results': results,
            }

        except Exception as e:
            err = str(e).lower()
            if '429' in err or 'rate' in err or 'blocked' in err or 'captcha' in err:
                with self._lock:
                    self._consecutive_429s += 1
                logger.warning(f"googlesearch rate-limited: {query[:60]}")
                self._inc(success=True)
                return {
                    'status': 'success',
                    'query': query,
                    'url': search_url,
                    'blocked': True,
                    'note': 'Google rate-limited — open URL manually.',
                    'results': [],
                }
            logger.error(f"googlesearch error for '{query[:60]}': {e}")
            # Fall back to requests
            return self._search_via_requests(query, max_results, search_url)

    # ── requests + bs4 backend ────────────────────────────────────────────

    def _search_via_requests(self, query: str, max_results: int, search_url: str) -> Dict:
        session = self._get_session()
        try:
            resp = session.get(search_url, timeout=15)

            if resp.status_code == 429:
                with self._lock:
                    self._consecutive_429s += 1
                back_off = min(15 + self._consecutive_429s * 5, 90)
                logger.warning(f"429 — backing off {back_off}s")
                time.sleep(back_off)
                self._inc(success=True)
                return {
                    'status': 'success',
                    'query': query,
                    'url': search_url,
                    'blocked': True,
                    'note': 'Google rate-limited — open URL manually.',
                    'results': [],
                }

            resp.raise_for_status()
            parsed = self._parse_html(resp.text, max_results) if BS4_AVAILABLE else []
            self._inc(success=True)
            return {
                'status': 'success',
                'query': query,
                'url': search_url,
                'blocked': len(parsed) == 0,
                'results': parsed,
            }

        except requests.exceptions.HTTPError as e:
            code = e.response.status_code if e.response else '?'
            self._inc(success=True)
            return {
                'status': 'success',
                'query': query,
                'url': search_url,
                'blocked': True,
                'note': f'HTTP {code} — open URL manually.',
                'results': [],
            }
        except requests.RequestException as e:
            logger.error(f"Request failed '{query[:60]}': {e}")
            self._inc(success=False)
            return {
                'status': 'error',
                'query': query,
                'url': search_url,
                'error': str(e),
                'results': [],
            }

    # ── HTML parsing ──────────────────────────────────────────────────────

    def _parse_html(self, html: str, max_results: int) -> List[Dict]:
        try:
            soup = BeautifulSoup(html, BS4_PARSER)
            results = []
            containers = (
                soup.select('div.g')
                or soup.select('div.tF2Cxc')
                or soup.select('div[data-sokoban-container]')
            )
            for c in containers[:max_results]:
                try:
                    title_el = c.find('h3')
                    link_el  = c.find('a')
                    desc_el  = (
                        c.find('div', {'class': 'VwiC3b'})
                        or c.find('span', {'class': 'st'})
                    )
                    if not (title_el and link_el):
                        continue
                    href = link_el.get('href', '')
                    if href.startswith('/url?q='):
                        href = unquote(href.split('/url?q=')[1].split('&')[0])
                    # Skip google.com URLs entirely
                    if not href.startswith('http') or 'google.com' in href:
                        continue
                    results.append({
                        'title': title_el.get_text(strip=True),
                        'url': href,
                        'description': desc_el.get_text(strip=True) if desc_el else '',
                    })
                except Exception:
                    continue
            return results
        except Exception as e:
            logger.error(f"HTML parse error: {e}")
            return []

    # ── helpers ───────────────────────────────────────────────────────────

    @staticmethod
    def _url_to_title(url: str) -> str:
        """Generate a readable title from a URL when we have no HTML to parse."""
        try:
            from urllib.parse import urlparse
            p = urlparse(url)
            parts = [x for x in p.path.strip('/').split('/') if x]
            label = parts[-1].replace('-', ' ').replace('_', ' ').title() if parts else p.netloc
            return f"{p.netloc} — {label}" if parts else p.netloc
        except Exception:
            return url

    def search_batch(self, queries: List[str], max_results: int = 5) -> List[Dict]:
        return [self.search(q, max_results) for q in queries]

    def get_stats(self) -> Dict:
        with self._lock:
            t, s, f = self.total_queries, self.successful_queries, self.failed_queries
        return {
            'total_queries': t,
            'successful_queries': s,
            'failed_queries': f,
            'success_rate': round((s / t * 100) if t > 0 else 0, 1),
        }
