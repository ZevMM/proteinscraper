import base64

from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding, rsa

from protein_scraper.walmart_auth import build_auth_headers, load_rsa_private_key


def _pem_key() -> tuple[rsa.RSAPrivateKey, str]:
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    pem = key.private_bytes(
        serialization.Encoding.PEM,
        serialization.PrivateFormat.TraditionalOpenSSL,
        serialization.NoEncryption(),
    ).decode()
    return key, pem


def test_headers_present_and_signature_verifies():
    key, pem = _pem_key()
    headers = build_auth_headers("consumer-123", pem, "2", timestamp_ms=1700000000000)

    assert headers["WM_CONSUMER.ID"] == "consumer-123"
    assert headers["WM_CONSUMER.INTIMESTAMP"] == "1700000000000"
    assert headers["WM_SEC.KEY_VERSION"] == "2"

    # The signed string is consumerId\ntimestamp\nkeyVersion\n (RSA-SHA256).
    signed = b"consumer-123\n1700000000000\n2\n"
    signature = base64.b64decode(headers["WM_SEC.AUTH_SIGNATURE"])
    # Raises InvalidSignature if wrong — so reaching the end means it verified.
    key.public_key().verify(signature, signed, padding.PKCS1v15(), hashes.SHA256())


def test_loader_accepts_openssh_format():
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    openssh = key.private_bytes(
        serialization.Encoding.PEM,
        serialization.PrivateFormat.OpenSSH,
        serialization.NoEncryption(),
    ).decode()
    assert "OPENSSH PRIVATE KEY" in openssh
    loaded = load_rsa_private_key(openssh)
    assert loaded.key_size == 2048
