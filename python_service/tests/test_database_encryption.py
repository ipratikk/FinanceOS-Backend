import os
import pytest
from crypto.database_encryption import encrypt, decrypt, hmac_fingerprint

FIXTURE_KEY_B64 = "U8tnbclQVVEUNzwLJnolbbWQMQuJsWT0zscl3Y9ppQI="
FIXTURE_COMBINED_B64 = "AAAAAAAAAAAAAAAATcnnQwD0zPLEOm1Lv34+K2YUzKOnO+tl8/Ej/WNNwRI="
FIXTURE_PLAINTEXT = "SWIGGY BANGALORE"


@pytest.fixture(autouse=True)
def _set_key(monkeypatch):
    monkeypatch.setenv("DATABASE_ENCRYPTION_KEY", FIXTURE_KEY_B64)


def test_encrypt_decrypt_round_trip():
    ciphertext = encrypt("some narration text")
    assert ciphertext != "some narration text"
    assert decrypt(ciphertext) == "some narration text"


def test_encrypt_none_passes_through():
    assert encrypt(None) is None


def test_decrypt_none_passes_through():
    assert decrypt(None) is None


def test_decrypt_fixture_produced_by_the_documented_wire_format():
    # Uses the exact fixture from Step 1 — decrypting it directly (bypassing
    # the normal random-nonce encrypt() path) proves this module's decrypt()
    # correctly parses the nonce(12)||ciphertext||tag(16) layout, which is
    # what Task 2's Node-side interop test also verifies independently.
    assert decrypt(FIXTURE_COMBINED_B64) == FIXTURE_PLAINTEXT


def test_hmac_fingerprint_is_deterministic():
    raw = "15/03/24|SWIGGY BANGALORE|50000|0"
    assert hmac_fingerprint(raw) == hmac_fingerprint(raw)


def test_hmac_fingerprint_differs_for_different_input():
    assert hmac_fingerprint("a") != hmac_fingerprint("b")


def test_hmac_fingerprint_matches_known_fixture():
    # Independently computed with the same DATABASE_ENCRYPTION_KEY this
    # test file's autouse fixture sets (FIXTURE_KEY_B64), confirming
    # hmac_fingerprint's actual output matches a real fixture — not just
    # its own internal consistency (covered by the determinism test above).
    raw = "15/03/24|SWIGGY BANGALORE|50000|0"
    expected = "08366b7663af513221c47139a4d2be79873d245779be9e2db7b89ed37a75ad47"
    assert hmac_fingerprint(raw) == expected


def test_missing_key_raises_at_import(monkeypatch):
    monkeypatch.delenv("DATABASE_ENCRYPTION_KEY", raising=False)
    import importlib
    import crypto.database_encryption as mod
    with pytest.raises(RuntimeError):
        importlib.reload(mod)
    # Restore for subsequent tests in this file
    monkeypatch.setenv("DATABASE_ENCRYPTION_KEY", FIXTURE_KEY_B64)
    importlib.reload(mod)
