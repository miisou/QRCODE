import uuid

def generate_nonce() -> str:
    """Generates a unique nonce (UUID4)."""
    return str(uuid.uuid4())
