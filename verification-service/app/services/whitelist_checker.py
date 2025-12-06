import json
import os
from urllib.parse import urlparse
from typing import List

class WhitelistChecker:
    def __init__(self, data_path: str = "app/data/official_domains.json"):
        # Go up two levels from services/whitelist_checker.py to app/ then to data/
        # Or relative from execution root. Let's assume execution from verification-service/
        self.data_path = data_path
        self._whitelist: List[str] = []
        self._load_whitelist()

    def _load_whitelist(self):
        try:
            with open(self.data_path, "r") as f:
                self._whitelist = json.load(f)
        except Exception as e:
            print(f"Error loading whitelist: {e}")
            self._whitelist = []

    def is_trusted(self, url: str) -> bool:
        # Reload for MVP dynamic updates
        self._load_whitelist()
        try:
            parsed = urlparse(url)
            domain = parsed.netloc
            # Simple check: domain is in whitelist
            # Ideally we check for "endswith" to allow subdomains if required, 
            # but MVP checking "gov.pl" vs "podatki.gov.pl" implies exact match or intelligent check.
            # Plan example: "gov.pl", "podatki.gov.pl" in list. So we check exact match or subdomain.
            # Let's do exact match for simplicity as per plan, or simple subdomain check.
            
            if domain in self._whitelist:
                return True
            
            # Allow subdomains if parent is in whitelist? 
            # For this MVP let's assume the json contains the exact host needed or we check extension.
            # Let's just iterate and check if domain ends with any allowed domain?
            # actually "gov.pl" is in the list, so "podatki.gov.pl" should probably match?
            # But the example list had both. Let's stick to simple list membership for safety.
            return domain in self._whitelist
        except:
            return False

whitelist_checker = WhitelistChecker()
