"""
Recon Engine — passive subdomain + info enumeration using free APIs.
No Google required. Works independently of the dorking scan.

Sources used:
  - crt.sh          (certificate transparency logs)
  - HackerTarget    (free API, no key needed)
  - ThreatCrowd     (free API)
  - AlienVault OTX  (free API)
  - DNS brute-force (common wordlist, dnspython)
  - SecurityTrails  (if API key provided)
"""

import requests
import json
import re
import socket
import concurrent.futures
import logging
from typing import List, Dict, Set
from datetime import datetime

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (compatible; security-recon/1.0)',
    'Accept': 'application/json',
}
TIMEOUT = 15

# Common subdomain wordlist for brute-force
COMMON_SUBDOMAINS = [
    'www', 'mail', 'ftp', 'smtp', 'pop', 'ns1', 'ns2', 'webmail', 'admin',
    'blog', 'dev', 'staging', 'test', 'api', 'app', 'portal', 'vpn', 'remote',
    'secure', 'shop', 'store', 'support', 'help', 'docs', 'static', 'cdn',
    'img', 'images', 'media', 'assets', 'files', 'download', 'downloads',
    'upload', 'uploads', 'git', 'gitlab', 'github', 'jenkins', 'ci', 'jira',
    'confluence', 'wiki', 'kb', 'forum', 'community', 'status', 'monitor',
    'dashboard', 'panel', 'cpanel', 'whm', 'plesk', 'mx', 'mx1', 'mx2',
    'mail2', 'email', 'imap', 'pop3', 'smtp2', 'exchange', 'owa', 'autodiscover',
    'mobile', 'm', 'wap', 'beta', 'alpha', 'preview', 'demo', 'old', 'new',
    'v1', 'v2', 'internal', 'intranet', 'extranet', 'private', 'public',
    'server', 'host', 'web', 'web1', 'web2', 'srv', 'lb', 'proxy', 'gateway',
    'router', 'fw', 'firewall', 'dmz', 'backup', 'bk', 'db', 'database',
    'mysql', 'postgres', 'mongo', 'redis', 'elastic', 'search', 'kibana',
    'grafana', 'prometheus', 'k8s', 'kubernetes', 'docker', 'registry',
    'repo', 'nexus', 'artifactory', 'sonar', 'build', 'deploy', 'prod',
    'production', 'uat', 'qa', 'sandbox', 'localhost', 'corp', 'office',
    'crm', 'erp', 'hr', 'finance', 'accounting', 'legal', 'marketing',
    'analytics', 'tracking', 'pixel', 'ads', 'affiliate', 'partner',
    'careers', 'jobs', 'news', 'press', 'ir', 'investor', 'about',
    'contact', 'login', 'auth', 'sso', 'oauth', 'id', 'account', 'accounts',
    'pay', 'payment', 'billing', 'invoice', 'checkout', 'cart', 'order',
    'orders', 'returns', 'track', 'shipping', 'logistics',
]


def _get(url: str, params: dict = None, timeout: int = TIMEOUT) -> requests.Response:
    return requests.get(url, headers=HEADERS, params=params, timeout=timeout)


# ── Source functions ──────────────────────────────────────────────────────────

def enum_crtsh(domain: str) -> List[Dict]:
    """Certificate Transparency via crt.sh — most reliable free source."""
    results = []
    try:
        resp = _get('https://crt.sh/', params={'q': f'%.{domain}', 'output': 'json'})
        if resp.status_code != 200:
            return results
        data = resp.json()
        seen: Set[str] = set()
        for entry in data:
            names = entry.get('name_value', '')
            for name in names.split('\n'):
                name = name.strip().lower().lstrip('*.')
                if name.endswith(f'.{domain}') or name == domain:
                    if name not in seen:
                        seen.add(name)
                        results.append({
                            'subdomain': name,
                            'source': 'crt.sh',
                            'ip': '',
                            'extra': f"Issuer: {entry.get('issuer_name','?')[:60]}",
                        })
    except Exception as e:
        logger.warning(f"crt.sh error: {e}")
    return results


def enum_hackertarget(domain: str) -> List[Dict]:
    """HackerTarget free API — no key needed, 100 req/day limit."""
    results = []
    try:
        resp = _get(f'https://api.hackertarget.com/hostsearch/?q={domain}')
        if resp.status_code != 200 or 'error' in resp.text.lower()[:30]:
            return results
        for line in resp.text.strip().split('\n'):
            if ',' in line:
                sub, ip = line.split(',', 1)
                sub = sub.strip().lower()
                if sub.endswith(f'.{domain}') or sub == domain:
                    results.append({
                        'subdomain': sub,
                        'source': 'HackerTarget',
                        'ip': ip.strip(),
                        'extra': '',
                    })
    except Exception as e:
        logger.warning(f"HackerTarget error: {e}")
    return results


def enum_alienvault(domain: str) -> List[Dict]:
    """AlienVault OTX passive DNS — free, no key needed."""
    results = []
    try:
        resp = _get(f'https://otx.alienvault.com/api/v1/indicators/domain/{domain}/passive_dns')
        if resp.status_code != 200:
            return results
        data = resp.json()
        seen: Set[str] = set()
        for record in data.get('passive_dns', []):
            hostname = record.get('hostname', '').lower().strip()
            if hostname.endswith(f'.{domain}') or hostname == domain:
                if hostname not in seen:
                    seen.add(hostname)
                    results.append({
                        'subdomain': hostname,
                        'source': 'AlienVault OTX',
                        'ip': record.get('address', ''),
                        'extra': f"Last seen: {record.get('last','?')[:10]}",
                    })
    except Exception as e:
        logger.warning(f"AlienVault error: {e}")
    return results


def enum_threatcrowd(domain: str) -> List[Dict]:
    """ThreatCrowd free API."""
    results = []
    try:
        resp = _get('https://www.threatcrowd.org/searchApi/v2/domain/report/',
                    params={'domain': domain})
        if resp.status_code != 200:
            return results
        data = resp.json()
        for sub in data.get('subdomains', []):
            sub = sub.lower().strip()
            if sub.endswith(f'.{domain}') or sub == domain:
                results.append({
                    'subdomain': sub,
                    'source': 'ThreatCrowd',
                    'ip': '',
                    'extra': '',
                })
    except Exception as e:
        logger.warning(f"ThreatCrowd error: {e}")
    return results


def enum_dns_bruteforce(domain: str, wordlist: List[str] = None) -> List[Dict]:
    """DNS resolution brute-force against common subdomain wordlist."""
    if wordlist is None:
        wordlist = COMMON_SUBDOMAINS
    results = []

    def resolve(sub):
        fqdn = f"{sub}.{domain}"
        try:
            ip = socket.gethostbyname(fqdn)
            return {'subdomain': fqdn, 'source': 'DNS brute-force', 'ip': ip, 'extra': ''}
        except socket.gaierror:
            return None

    with concurrent.futures.ThreadPoolExecutor(max_workers=50) as ex:
        futures = {ex.submit(resolve, s): s for s in wordlist}
        for fut in concurrent.futures.as_completed(futures):
            r = fut.result()
            if r:
                results.append(r)

    return results


def resolve_ips(subdomains: List[Dict]) -> List[Dict]:
    """Fill in missing IPs via DNS resolution."""
    def fill(entry):
        if not entry.get('ip'):
            try:
                entry['ip'] = socket.gethostbyname(entry['subdomain'])
            except Exception:
                entry['ip'] = ''
        return entry

    with concurrent.futures.ThreadPoolExecutor(max_workers=30) as ex:
        return list(ex.map(fill, subdomains))


# ── Main enumerate function ───────────────────────────────────────────────────

def enumerate_subdomains(domain: str, brute_force: bool = True) -> Dict:
    """
    Run all passive sources + optional DNS brute-force.
    Returns a structured dict for the dashboard.
    """
    logger.info(f"Starting subdomain enumeration for {domain}")
    all_results: List[Dict] = []
    seen: Set[str] = set()
    source_counts: Dict[str, int] = {}

    sources = [
        ('crt.sh',          enum_crtsh),
        ('HackerTarget',    enum_hackertarget),
        ('AlienVault OTX',  enum_alienvault),
        ('ThreatCrowd',     enum_threatcrowd),
    ]

    for source_name, fn in sources:
        logger.info(f"  Querying {source_name}…")
        try:
            items = fn(domain)
            count = 0
            for item in items:
                sub = item['subdomain']
                if sub not in seen:
                    seen.add(sub)
                    all_results.append(item)
                    count += 1
            source_counts[source_name] = count
            logger.info(f"  {source_name}: {count} unique subdomains")
        except Exception as e:
            logger.error(f"  {source_name} failed: {e}")
            source_counts[source_name] = 0

    if brute_force:
        logger.info("  Running DNS brute-force…")
        bf_results = enum_dns_bruteforce(domain)
        count = 0
        for item in bf_results:
            if item['subdomain'] not in seen:
                seen.add(item['subdomain'])
                all_results.append(item)
                count += 1
        source_counts['DNS brute-force'] = count
        logger.info(f"  DNS brute-force: {count} unique subdomains")

    # Fill missing IPs
    logger.info("  Resolving IPs…")
    all_results = resolve_ips(all_results)

    # Sort: brute-force last, alphabetical otherwise
    all_results.sort(key=lambda x: (x['source'] == 'DNS brute-force', x['subdomain']))

    return {
        'domain': domain,
        'scan_date': datetime.now().isoformat(),
        'total': len(all_results),
        'source_counts': source_counts,
        'subdomains': all_results,
    }
