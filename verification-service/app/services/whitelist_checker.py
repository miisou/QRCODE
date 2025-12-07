import time
import requests
import os
from urllib.parse import urlparse
from typing import Set
from app.core.config import settings


class TrustAnchorRepository:
    def __init__(self, api_url: str = None, cache_ttl: int = 3600):
        """
        Initialize TrustAnchorRepository with API-based whitelist.
        
        Args:
            api_url: URL to the Polish government API for domain whitelist
            cache_ttl: Cache time-to-live in seconds (default: 1 hour)
        """
        self.api_url = api_url or "https://api.dane.gov.pl/1.4/resources/63616,lista-nazw-domeny-govpl-z-usuga-www/data"
        self.cache_ttl = cache_ttl
        
        # Cache for domains set
        self._domains_cache: Set[str] = set()
        self._cache_timestamp: float = 0
        
        # Load initial whitelist
        self._load_repository()

    def _fetch_all_pages(self) -> Set[str]:
        """
        Fetch all domains from the API, handling pagination.
        Returns a set of domain names.
        """
        domains = set()
        next_url = self.api_url
        page = 1
        
        try:
            while next_url:
                print(f"  → Fetching page {page} from API...")
                response = requests.get(next_url, timeout=10)
                response.raise_for_status()
                
                data = response.json()
                
                # Extract domains from JSON:API format
                # Domains are in data[].attributes.col1.val
                if "data" in data:
                    for item in data["data"]:
                        if "attributes" in item and "col1" in item["attributes"]:
                            domain = item["attributes"]["col1"].get("val")
                            if domain:
                                # Normalize domain (lowercase, strip whitespace)
                                domain = domain.lower().strip()
                                domains.add(domain)
                                # Also add without www. prefix for matching (e.g., www.gov.pl -> gov.pl)
                                # This allows matching both www.gov.pl and gov.pl
                                if domain.startswith("www."):
                                    domains.add(domain[4:])
                
                # Check for next page
                if "links" in data and "next" in data["links"]:
                    next_url = data["links"]["next"]
                    page += 1
                else:
                    next_url = None
                
                # Small delay to avoid rate limiting
                time.sleep(0.1)
            
            print(f"  → Fetched {page} page(s), total {len(domains)} unique domains")
            return domains
            
        except requests.exceptions.RequestException as e:
            print(f"❌ ERROR fetching whitelist from API: {e}")
            raise
        except Exception as e:
            print(f"❌ ERROR parsing API response: {e}")
            raise

    def _load_repository(self):
        """
        Load whitelist from API and cache it.
        Uses cached data if still valid.
        """
        # Check if cache is still valid
        current_time = time.time()
        if self._domains_cache and (current_time - self._cache_timestamp) < self.cache_ttl:
            print(f"✅ Using cached whitelist ({len(self._domains_cache)} domains)")
            return
        
        try:
            print(f"🔄 Fetching whitelist from API: {self.api_url}")
            domains = self._fetch_all_pages()
            
            if domains:
                self._domains_cache = domains
                self._cache_timestamp = current_time
                print(f"✅ Loaded {len(self._domains_cache)} domains from API whitelist")
            else:
                raise ValueError("No domains fetched from API")
                
        except Exception as e:
            print(f"❌ ERROR loading TAR from API: {e}")
            # Initialize with hardcoded fallback for critical domains
            self._domains_cache = {
                "gov.pl",
                "www.gov.pl",
                "podatki.gov.pl",
                "moje.gov.pl",
                "pacjent.gov.pl",
                "profil-zaufany.pl"
            }
            print(f"⚠️  Using fallback whitelist with {len(self._domains_cache)} domains")

    def is_trusted(self, url: str) -> bool:
        """
        Check if a URL's domain is in the trusted whitelist.
        Supports exact match and parent domain matching.
        If TEST_SSL=True, allows all badssl.com subdomains for testing.
        """
        # Reload if cache expired
        self._load_repository()
        
        try:
            parsed = urlparse(url)
            domain = parsed.netloc.lower().strip()
            
            # Remove port if present
            if ':' in domain:
                domain = domain.split(':')[0]
            
            # TEST_SSL mode: Allow all badssl.com subdomains for SSL testing
            if settings.TEST_SSL and domain.endswith(".badssl.com"):
                print(f"  → TEST_SSL mode: Allowing badssl.com domain: {domain}")
                return True
            
            # Check for exact match
            if domain in self._domains_cache:
                return True
            
            # Also check without www. prefix if domain starts with www.
            if domain.startswith("www."):
                domain_without_www = domain[4:]
                if domain_without_www in self._domains_cache:
                    return True
            
            # Check for parent domains if not exact match
            # e.g. "auth.podatki.gov.pl" -> checks "podatki.gov.pl", then "gov.pl"
            parts = domain.split('.')
            for i in range(1, len(parts)):  # Check all parent domains
                parent = ".".join(parts[i:])
                if parent in self._domains_cache:
                    return True
                # Also check parent without www. prefix
                if parent.startswith("www."):
                    parent_without_www = parent[4:]
                    if parent_without_www in self._domains_cache:
                        return True
            
            return False
        except Exception as e:
            print(f"⚠️  Error checking domain trust: {e}")
            return False

    def get_policy(self, domain: str) -> dict:
        """
        Get policy for a domain (for compatibility).
        Returns default policy since API doesn't provide policy info.
        """
        if domain in self._domains_cache:
            return {"policy": "strict", "allowed_cas": []}
        return {}

# Global instance
trust_anchor_repository = TrustAnchorRepository()

