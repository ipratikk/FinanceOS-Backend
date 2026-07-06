import base64
import hashlib
import hmac
import os

from cryptography.hazmat.primitives.ciphers.aead import AESGCM

_KEY_ENV_VAR = "DATABASE_ENCRYPTION_KEY"


def _load_key() -> bytes:
    raw = os.environ.get(_KEY_ENV_VAR)
    if not raw:
        raise RuntimeError(f"{_KEY_ENV_VAR} is not set")
    key = base64.b64decode(raw)
    if len(key) != 32:
        raise RuntimeError(f"{_KEY_ENV_VAR} must decode to exactly 32 bytes, got {len(key)}")
    return key


_KEY = _load_key()


def encrypt(plaintext: str | None) -> str | None:
    if plaintext is None:
        return None
    nonce = os.urandom(12)
    aesgcm = AESGCM(_KEY)
    ciphertext_with_tag = aesgcm.encrypt(nonce, plaintext.encode("utf-8"), None)
    combined = nonce + ciphertext_with_tag
    return base64.b64encode(combined).decode("ascii")


def decrypt(ciphertext: str | None) -> str | None:
    if ciphertext is None:
        return None
    combined = base64.b64decode(ciphertext)
    nonce = combined[:12]
    ciphertext_with_tag = combined[12:]
    aesgcm = AESGCM(_KEY)
    plaintext = aesgcm.decrypt(nonce, ciphertext_with_tag, None)
    return plaintext.decode("utf-8")


def hmac_fingerprint(raw: str) -> str:
    """Deterministic HMAC-SHA256 of `raw`, hex-encoded.

    Intentionally reuses the same DATABASE_ENCRYPTION_KEY as encrypt/decrypt —
    HMAC-SHA256 and AES-256-GCM are cryptographically independent uses of the
    same key material. Do not introduce a second key here; that would
    silently invalidate every existing sourceFingerprint hash in the DB.
    """
    return hmac.new(_KEY, raw.encode("utf-8"), hashlib.sha256).hexdigest()
