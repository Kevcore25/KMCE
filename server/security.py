"""Request validation: IP whitelist + API key."""

import hashlib
import logging
import secrets
import socket
import threading
from typing import Annotated

from dns import resolver
from fastapi import Depends, Header, HTTPException, Request

from server import config

log = logging.getLogger(__name__)

try:
    localIPs: list[str] = socket.gethostbyname_ex(socket.gethostname())[2]
except OSError:
    localIPs = []

validIPs: list[str] = localIPs + ["127.0.0.1"]


def ips_loop():
    """Refreshes the trusted IP list from DNS, then reschedules itself."""
    global validIPs
    t = threading.Timer(config.IP_REFRESH_SECONDS, ips_loop)
    t.daemon = True
    t.start()

    try:
        remote = resolver.resolve(config.IP_RECORD, "TXT")[0].to_text()[1:-1].split(',')
    except Exception:
        # Keep the previous list rather than crashing or locking everyone out
        log.exception("Unable to refresh trusted IPs from %s", config.IP_RECORD)
        return

    # Assign in one step so readers never see a half-built list
    validIPs = [ip.strip() for ip in remote if ip.strip()] + localIPs + ["127.0.0.1"]


def check_valid_ip(req: Request) -> bool:
    return req.client is not None and req.client.host in validIPs


def check_valid_key(key: str | None) -> bool:
    if not key:
        return False
    # Compare against every key so timing doesn't reveal which one (or how much) matched
    matched = False
    for valid in config.API_KEYS:
        matched |= secrets.compare_digest(key.encode(), valid.encode())
    return matched


def server_id_for(key: str) -> str:
    """A stable, non-secret ID for the Minecraft server that owns an API key."""
    return hashlib.sha256(key.encode()).hexdigest()[:16]


def require_trusted_client(
    request: Request,
    x_api_key: Annotated[str | None, Header()] = None,
) -> str:
    """Rejects untrusted requests and returns the calling server's ID."""
    if not check_valid_ip(request):
        raise HTTPException(status_code=403, detail="Untrusted client")
    if not check_valid_key(x_api_key):
        raise HTTPException(status_code=403, detail="Invalid API key")
    return server_id_for(x_api_key)


ClientDep = Annotated[str, Depends(require_trusted_client)]
