"""Server settings, read from environment variables."""

import os
from pathlib import Path

SERVER_DIR = Path(__file__).resolve().parent

# Comma-separated list of API keys. Each Minecraft server should get its own key.
# An empty list rejects every request.
API_KEYS: list[str] = [
    key.strip() for key in os.environ.get("KMCE_API_KEYS", "").split(",") if key.strip()
]

DB_URL: str = os.environ.get("KMCE_DB_URL", f"sqlite:///{SERVER_DIR / 'kmce.db'}")

# DNS TXT record listing the IPs of trusted Minecraft servers, refreshed periodically
IP_RECORD: str = os.environ.get("KMCE_IP_RECORD", "serverips.kcservers.ca")
IP_REFRESH_SECONDS: int = 300

# Global balance cap (same as the legacy system)
MAX_BALANCE: int = 1_000_000

# Gain limit: the most net KCash (deposits minus transfers out) a player can gain on one
# Minecraft server within a rolling window. Deposits that would exceed it are denied.
# A limit of 0 disables the check.
GAIN_LIMIT: int = int(os.environ.get("KMCE_GAIN_LIMIT", "200000"))
GAIN_WINDOW_MINUTES: int = int(os.environ.get("KMCE_GAIN_WINDOW_MINUTES", "180"))

# Minecraft username charset
USERNAME_PATTERN: str = r"^[A-Za-z0-9_]{1,16}$"
