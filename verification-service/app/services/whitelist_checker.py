import json
import os
from urllib.parse import urlparse
from typing import List


class TrustAnchorRepository:
    def __init__(self, data_path: str = "app/data/official_domains.json"):
        self.data_path = data_path
        self._repository: dict = {}
        self._load_repository()

    def _load_repository(self):
        try:
            with open(self.data_path, "r") as f:
                self._repository = json.load(f)
        except Exception as e:
            print(f"Error loading TAR: {e}")
            self._repository = {}

    def is_trusted(self, url: str) -> bool:
        # Reload for dynamic updates
        self._load_repository()
        try:
            parsed = urlparse(url)
            domain = parsed.netloc
            # Check for exact match or strict policy logic
            if domain in self._repository:
                return True
                
            # TODO: Implement subdomain recursion if policy allows? 
            # For strict policy, we might only allow exact matches from keys.
            return False
        except:
            return False

    def get_policy(self, domain: str) -> dict:
        return self._repository.get(domain, {})

# Global instance
trust_anchor_repository = TrustAnchorRepository()

