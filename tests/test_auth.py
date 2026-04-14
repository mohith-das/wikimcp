"""Tests for wikimcp.server.auth — hash_token and validate_token."""
import pytest

from wikimcp.server.auth import hash_token, validate_token


def test_hash_token_returns_hex_string() -> None:
    result = hash_token("mytoken")
    assert isinstance(result, str)
    assert len(result) == 64  # SHA-256 hex is 64 chars
    assert all(c in "0123456789abcdef" for c in result)


def test_hash_token_is_deterministic() -> None:
    assert hash_token("abc") == hash_token("abc")


def test_hash_token_different_inputs_differ() -> None:
    assert hash_token("tokenA") != hash_token("tokenB")


def test_validate_token_returns_username_for_valid_token() -> None:
    token = "wikimcp_alice_aabbccdd"
    token_hash = hash_token(token)
    config = {
        "users": {
            "alice": {"token_hash": token_hash},
        }
    }
    result = validate_token(token, config)
    assert result == "alice"


def test_validate_token_returns_none_for_wrong_token() -> None:
    token_hash = hash_token("wikimcp_alice_correct")
    config = {
        "users": {
            "alice": {"token_hash": token_hash},
        }
    }
    result = validate_token("wikimcp_alice_wrong", config)
    assert result is None


def test_validate_token_returns_none_for_empty_token() -> None:
    config = {"users": {"alice": {"token_hash": hash_token("some_token")}}}
    result = validate_token("", config)
    assert result is None


def test_validate_token_returns_none_for_empty_users() -> None:
    result = validate_token("any_token", {"users": {}})
    assert result is None


def test_validate_token_multiple_users_correct_match() -> None:
    token_alice = "wikimcp_alice_aaa"
    token_bob = "wikimcp_bob_bbb"
    config = {
        "users": {
            "alice": {"token_hash": hash_token(token_alice)},
            "bob": {"token_hash": hash_token(token_bob)},
        }
    }
    assert validate_token(token_alice, config) == "alice"
    assert validate_token(token_bob, config) == "bob"
    assert validate_token("wikimcp_eve_xxx", config) is None
