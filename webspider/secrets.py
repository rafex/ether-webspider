"""Ephemeral, Keychain and encrypted-file credential resolution."""

from __future__ import annotations

import base64
import hashlib
import json
import os
import stat
from pathlib import Path
from typing import Any, cast


def _fernet():
    try:
        from cryptography.fernet import Fernet
    except ImportError as exc:
        raise RuntimeError("Encrypted credential storage requires the optional 'security' dependencies") from exc
    key = os.environ.get("WEBSPIDER_SECRET_KEY", "")
    if not key:
        raise RuntimeError("WEBSPIDER_SECRET_KEY is required for encrypted credential storage")
    derived = base64.urlsafe_b64encode(hashlib.sha256(key.encode()).digest())
    return Fernet(derived)


def _secret_file() -> Path:
    return Path(os.environ.get("WEBSPIDER_SECRET_FILE", "~/.webspider/secrets.json")).expanduser()


def put_encrypted(ref: str, value: dict[str, str]) -> str:
    """Store an explicitly requested credential bundle encrypted on disk."""
    path = _secret_file()
    path.parent.mkdir(parents=True, exist_ok=True)
    data: dict[str, Any] = {}
    if path.is_file():
        data = json.loads(path.read_text(encoding="utf-8"))
    token = _fernet().encrypt(json.dumps(value).encode()).decode()
    data[ref] = token
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")
    os.chmod(path, stat.S_IRUSR | stat.S_IWUSR)
    return str(path)


def get_encrypted(ref: str) -> dict[str, str]:
    path = _secret_file()
    if not path.is_file():
        raise KeyError(f"Encrypted credential reference not found: {ref}")
    data = json.loads(path.read_text(encoding="utf-8"))
    token = data.get(ref)
    if not token:
        raise KeyError(f"Encrypted credential reference not found: {ref}")
    return cast(dict[str, str], json.loads(_fernet().decrypt(token.encode()).decode()))


def get_keychain(ref: str) -> dict[str, str]:
    try:
        import keyring
    except ImportError as exc:
        raise RuntimeError("Keychain credentials require the optional 'security' dependencies") from exc
    raw = keyring.get_password("webspider", ref)
    if not raw:
        raise KeyError(f"Keychain credential reference not found: {ref}")
    value = json.loads(raw)
    if not isinstance(value, dict):
        raise ValueError("Keychain credential must be a JSON object")
    return {str(key): str(item) for key, item in value.items()}


def resolve_credentials(explicit: dict[str, str] | None = None, reference: str | None = None) -> dict[str, str]:
    """Resolve credentials with explicit input taking precedence over references."""
    if explicit:
        return dict(explicit)
    if not reference:
        return {}
    if reference.startswith("keychain:"):
        return get_keychain(reference.removeprefix("keychain:"))
    if reference.startswith("file:"):
        return get_encrypted(reference.removeprefix("file:"))
    try:
        return get_keychain(reference)
    except (KeyError, RuntimeError):
        return get_encrypted(reference)
