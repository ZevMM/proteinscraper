"""Walmart IO Affiliate API digital-signature authentication.

Each request is signed with the registered RSA private key. The signing string
is ``consumerId\\ntimestamp\\nkeyVersion\\n`` (RSA-SHA256, PKCS#1 v1.5), and the
result goes in the ``WM_SEC.AUTH_SIGNATURE`` header alongside the consumer id,
timestamp, and key version.

Refs: walmart.io affiliate docs; j5bot/vandevliet implementations.
"""

from __future__ import annotations

import base64
import time

from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding, rsa
from cryptography.hazmat.primitives.asymmetric.types import PrivateKeyTypes


def load_rsa_private_key(key_text: str) -> rsa.RSAPrivateKey:
    """Load an RSA private key from PEM (PKCS#1/#8) or OpenSSH format."""
    data = key_text.encode()
    key: PrivateKeyTypes
    if "OPENSSH PRIVATE KEY" in key_text:
        key = serialization.load_ssh_private_key(data, password=None)
    else:
        key = serialization.load_pem_private_key(data, password=None)
    if not isinstance(key, rsa.RSAPrivateKey):
        raise TypeError("Walmart private key must be an RSA private key")
    return key


def build_auth_headers(
    consumer_id: str, private_key_pem: str, key_version: str, *, timestamp_ms: int | None = None
) -> dict[str, str]:
    """Return the four Walmart auth headers for one request."""
    timestamp = str(timestamp_ms if timestamp_ms is not None else int(time.time() * 1000))
    data = f"{consumer_id}\n{timestamp}\n{key_version}\n".encode()

    key = load_rsa_private_key(private_key_pem)
    signature = base64.b64encode(key.sign(data, padding.PKCS1v15(), hashes.SHA256())).decode()

    return {
        "WM_CONSUMER.ID": consumer_id,
        "WM_CONSUMER.INTIMESTAMP": timestamp,
        "WM_SEC.KEY_VERSION": str(key_version),
        "WM_SEC.AUTH_SIGNATURE": signature,
        "Accept": "application/json",
    }
