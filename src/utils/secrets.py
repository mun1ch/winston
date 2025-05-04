import os
from dotenv import load_dotenv

# Load environment variables from a .env file
load_dotenv()

def get_secret(key: str) -> str:
    """Retrieve a secret from environment variables."""
    value = os.getenv(key)
    if not value:
        raise ValueError(f"Secret for {key} not found in environment variables.")
    return value