"""
Google Search Module

Priority order:
  1. Google Custom Search API  (no rate-limits, requires GOOGLE_API_KEY + GOOGLE_SEARCH_ENGINE_ID)
  2. googlesearch-python       (free, moderate rate-limits)
  3. requests + BeautifulSoup  (free, most likely to get blocked)

Set GOOGLE_API_KEY and GOOGLE_SEARCH_ENGINE_ID in .env to eliminate rate-limiting.
Free tier: 100 queries/day. Paid: $5 per 1000 queries.
"""

import time
import threading
import random
import logging
from urllib.parse import quote, unquote
from typing import List, Dict, Optional

import requests

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

try:
    from googlesearch import search as gsearch
    GSEARCH_AVAILABLE = True
    logger.info("googlesearch-python available — using as secondary search backend")
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

# Rotate user-agents to reduce fingerprinting when scraping
_USER_AGENTS = [
    'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
    'Mozilla/5.0 (X11; Linux x86_64; rv:124.0) Gecko/20100101 Firefox/124.0',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:123.0) Gecko/20100101 Firefox/123.0',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 14_4) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4 Safari/605.1.15',
]


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

    Backend priority:
      1. Google Custom Search API  — set api_key + search_engine_id to enable
      2. googlesearch-python       — free, handles its own throttle
      3. requests + bs4            — last resort, most blockable

    Never returns the dork query URL itself as a finding.
    """

    GOOGLE_API_ENDPOINT = 'https://www.googleapis.com/customsearch/v1'

    def __init__(
        self,
        delay: float = 2.0,
        rate_limit: float = 0.5,
        api_key: Optional[str] = None,
        search_engine_id: Optional[str] = None,
    ):
        self.delay = delay
        self.rate_limiter = RateLimiter(rate=rate_limit)
        self._api_key = api_key
        self._search_engine_id = search_engine_id
        self._use_api = bool(api_key and search_engine_id)

        if self._use_api:
            logger.info("Google Custom Search API configured — rate-limiting disabled")

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
                'User-Agent': random.choice(_USER_AGENTS),
                'Accept-Language': 'en-US,en;q=0.9',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            })
            self._thread_local.session = s
        return self._thread_local.session

    def _rotate_ua(self):
        """Pick a fresh user-agent for this thread's session."""
        if hasattr(self._thread_local, 'session'):
            self._thread_local.session.headers['User-Agent'] = random.choice(_USER_AGENTS)

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
        Run one dork query. Returns a structured result dict.
        The Google search URL is stored in result['url'] for manual fallback
        but is NEVER included in result['results'] as a finding.
        """
        # Back-off when repeatedly rate-limited (scraping path only)
        if not self._use_api:
            with self._lock:
                consec = self._consecutive_429s
            if consec >= 3:
                extra = min(consec * 5, 60)
                logger.warning(f"Back-off extra {extra}s after {consec} consecutive 429s")
                time.sleep(extra)

            self.rate_limiter.acquire()
            self._rotate_ua()

        encoded    = quote(query)
        search_url = f"https://www.google.com/search?q={encoded}&num={max_results}&hl=en"

        if self._use_api:
            result = self._search_via_google_api(query, max_results, search_url)
        elif GSEARCH_AVAILABLE:
            result = self._search_via_library(query, max_results, search_url)
        else:
            result = self._search_via_requests(query, max_results, search_url)

        if not self._use_api and self.delay > 0:
            # Add random jitter (±20 %) to make traffic less predictable
            jitter = self.delay * random.uniform(0.8, 1.2)
            time.sleep(jitter)

        return result

    # ── Google Custom Search API backend ─────────────────────────────────

    def _search_via_google_api(self, query: str, max_results: int, search_url: str) -> Dict:
        """
        Official Google Custom Search JSON API.
        Free: 100 queries/day. Paid: $5 per 1,000 queries.
        No rate-limiting, no CAPTCHAs, always returns structured results.
        """
        try:
            params = {
                'key': self._api_key,
                'cx':  self._search_engine_id,
                'q':   query,
                'num': min(max_results, 10),  # API cap is 10 per request
            }
            resp = self._get_session().get(
                self.GOOGLE_API_ENDPOINT, params=params, timeout=15
            )
            resp.raise_for_status()
            data = resp.json()

            results = [
                {
                    'title':       item.get('title', ''),
                    'url':         item.get('link', ''),
                    'description': item.get('snippet', ''),
                }
                for item in data.get('items', [])
                if item.get('link') and 'google.com' not in item.get('link', '')
            ]

            self._inc(success=True)
            return {
                'status':  'success',
                'query':   query,
                'url':     search_url,
                'blocked': False,
                'via':     'google_api',
                'results': results,
            }

        except requests.exceptions.HTTPError as e:
            code = e.response.status_code if e.response else '?'
            logger.error(f"Google API HTTP {code} for '{query[:60]}'")
            if code == 429:
                # Quota exhausted — fall back to library
                logger.warning("Google API quota exhausted; falling back to scraping")
                return self._search_via_library(query, max_results, search_url) \
                    if GSEARCH_AVAILABLE \
                    else self._search_via_requests(query, max_results, search_url)
            self._inc(success=False)
            return {
                'status':  'error',
                'query':   query,
                'url':     search_url,
                'error':   f'Google API HTTP {code}',
                'results': [],
            }

        except Exception as e:
            logger.error(f"Google API error for '{query[:60]}': {e}")
            # Fall back to library
            return self._search_via_library(query, max_results, search_url) \
                if GSEARCH_AVAILABLE \
                else self._search_via_requests(query, max_results, search_url)

    # ── googlesearch-python backend ───────────────────────────────────────

    def _search_via_library(self, query: str, max_results: int, search_url: str) -> Dict:
        try:
            urls = list(gsearch(query, num_results=max_results, sleep_interval=2, lang="en"))
            results = []
            for url in urls:
                if 'google.com' in url:
                    continue
                results.append({
                    'title':       self._url_to_title(url),
                    'url':         url,
                    'description': '',
                })

            self._inc(success=True)
            return {
                'status':  'success',
                'query':   query,
                'url':     search_url,
                'blocked': False,
                'via':     'googlesearch_lib',
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
                    'status':  'success',
                    'query':   query,
                    'url':     search_url,
                    'blocked': True,
                    'via':     'googlesearch_lib',
                    'note':    'Google rate-limited — open URL manually or configure GOOGLE_API_KEY.',
                    'results': [],
                }
            logger.error(f"googlesearch error for '{query[:60]}': {e}")
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
                    'status':  'success',
                    'query':   query,
                    'url':     search_url,
                    'blocked': True,
                    'via':     'requests',
                    'note':    'Google rate-limited — open URL manually or configure GOOGLE_API_KEY.',
                    'results': [],
                }

            resp.raise_for_status()
            parsed = self._parse_html(resp.text, max_results) if BS4_AVAILABLE else []
            self._inc(success=True)
            return {
                'status':  'success',
                'query':   query,
                'url':     search_url,
                'blocked': len(parsed) == 0,
                'via':     'requests',
                'results': parsed,
            }

        except requests.exceptions.HTTPError as e:
            code = e.response.status_code if e.response else '?'
            self._inc(success=True)
            return {
                'status':  'success',
                'query':   query,
                'url':     search_url,
                'blocked': True,
                'via':     'requests',
                'note':    f'HTTP {code} — open URL manually or configure GOOGLE_API_KEY.',
                'results': [],
            }
        except requests.RequestException as e:
            logger.error(f"Request failed '{query[:60]}': {e}")
            self._inc(success=False)
            return {
                'status':  'error',
                'query':   query,
                'url':     search_url,
                'error':   str(e),
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
                    if not href.startswith('http') or 'google.com' in href:
                        continue
                    results.append({
                        'title':       title_el.get_text(strip=True),
                        'url':         href,
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
            'total_queries':      t,
            'successful_queries': s,
            'failed_queries':     f,
            'success_rate':       round((s / t * 100) if t > 0 else 0, 1),
            'api_mode':           self._use_api,
        }
