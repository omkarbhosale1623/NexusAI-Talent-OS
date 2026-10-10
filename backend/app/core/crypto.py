"""
Field-level encryption-at-rest for sensitive columns (ATS API keys, OAuth
tokens, etc.).

Uses Fernet (AES-128-CBC + HMAC). The key comes from `settings.ENCRYPTION_KEY`
(a urlsafe-base64 32-byte Fernet key) when set; otherwise it is deterministically
derived from `settings.SECRET_KEY` so encryption still works in dev — but in
production you MUST set a dedicated, rotated `ENCRYPTION_KEY` (see
`validate_production_secrets`).

Encrypted values are stored with an `enc::` prefix so `decrypt()` can transparently
pass through legacy/plaintext values during migration.
"""
import base64
import hashlib
import logging
from functools import lru_cache
from typing import Optional

from cryptography.fernet import Fernet, InvalidToken

from app.core.config import settings

logger = logging.getLogger(__name__)

_PREFIX = "enc::"


@lru_cache
def _fernet() -> Fernet:
    key = (settings.ENCRYPTION_KEY or "").strip()
    if key:
        try:
            return Fernet(key.encode())
        except Exception:
            logger.warning("ENCRYPTION_KEY is not a valid Fernet key; deriving from SECRET_KEY")
    # Derive a stable 32-byte key from SECRET_KEY (dev fallback only).
    digest = hashlib.sha256(settings.SECRET_KEY.encode()).digest()
    return Fernet(base64.urlsafe_b64encode(digest))


def is_encrypted(value: Optional[str]) -> bool:
    return bool(value) and value.startswith(_PREFIX)


def encrypt(plaintext: Optional[str]) -> Optional[str]:
    """Encrypt a string for storage. None/empty pass through unchanged."""
    if not plaintext:
        return plaintext
    if is_encrypted(plaintext):
        return plaintext
    token = _fernet().encrypt(plaintext.encode()).decode()
    return f"{_PREFIX}{token}"


def decrypt(value: Optional[str]) -> Optional[str]:
    """Decrypt a stored value. Legacy plaintext (no prefix) is returned as-is."""
    if not value or not is_encrypted(value):
        return value
    try:
        return _fernet().decrypt(value[len(_PREFIX):].encode()).decode()
    except InvalidToken:
        logger.error("Failed to decrypt value (wrong key or corrupted ciphertext)")
        return None


def mask_secret(value: Optional[str], keep: int = 4) -> str:
    """Return a masked representation for display/logging (never the plaintext)."""
    plain = decrypt(value) if is_encrypted(value) else value
    if not plain:
        return ""
    if len(plain) <= keep:
        return "*" * len(plain)
    return "*" * (len(plain) - keep) + plain[-keep:]


def generate_key() -> str:
    """Generate a fresh Fernet key (use for ENCRYPTION_KEY)."""
    return Fernet.generate_key().decode()
