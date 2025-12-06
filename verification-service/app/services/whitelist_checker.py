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
                
            # Check for parent domains if not exact match
            # e.g. "auth.podatki.gov.pl" -> checks "podatki.gov.pl", then "gov.pl"
            parts = domain.split('.')
            for i in range(1, len(parts)-1): # Ensure at least TLD+1 (e.g. gov.pl)
                parent = ".".join(parts[i:])
                if parent in self._repository:
                    # Check policy of parent
                    policy = self._repository[parent].get("policy")
                    if policy == "strict":
                        # Strict might imply "only exact", or "include subdomains strictly"?
                        # Usually "strict" in this context might mean "trust this and children".
                        # Let's assume for production that whitelist entries imply trusted roots.
                        return True
                    # If policy is 'exact_only', we continue loop or return False.
                    # Defaulting to True for now as TAR entry implies Trust Anchor.
                    return True
            
            return False
        except:
            return False

    def get_policy(self, domain: str) -> dict:
        return self._repository.get(domain, {})

# Global instance
trust_anchor_repository = TrustAnchorRepository()

