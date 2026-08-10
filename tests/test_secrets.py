"""Credential provider and no-plaintext persistence tests."""

from __future__ import annotations

import os
from unittest.mock import patch

import pytest


def test_explicit_credentials_take_precedence():
    from webspider.secrets import resolve_credentials

    with patch("webspider.secrets.get_keychain", side_effect=AssertionError("must not read store")):
        assert resolve_credentials({"user": "alice"}, "keychain:account") == {"user": "alice"}


def test_encrypted_credentials_round_trip(tmp_path):
    cryptography = pytest.importorskip("cryptography")
    del cryptography
    with patch.dict(
        os.environ,
        {
            "WEBSPIDER_SECRET_KEY": "local-test-key",
            "WEBSPIDER_SECRET_FILE": str(tmp_path / "secrets.json"),
        },
    ):
        from webspider.secrets import put_encrypted, resolve_credentials

        put_encrypted("orders", {"username": "alice", "password": "secret-value"})
        assert resolve_credentials(reference="file:orders") == {"username": "alice", "password": "secret-value"}
        assert "secret-value" not in (tmp_path / "secrets.json").read_text()
