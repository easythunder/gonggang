"""Unit tests for nickname generation library."""
import pytest
from src.lib.nickname import (
    generate_nickname,
    validate_nickname_format,
)


def test_generate_nickname_format():
    """Test that generated nicknames follow word_word_word format."""
    nickname = generate_nickname()
    assert isinstance(nickname, str)
    parts = nickname.split("_")
    assert len(parts) == 3
    assert all(len(p) > 0 for p in parts)


def test_generate_nickname_uniqueness():
    """Test that repeatedly generated nicknames are different."""
    nicknames = set()
    for _ in range(10):
        nickname = generate_nickname()
        assert nickname not in nicknames
        nicknames.add(nickname)


def test_generate_nickname_avoids_excluded():
    """Test that exclude set prevents duplicate generation."""
    excluded = {"happy_bright_lion", "swift_silver_mountain"}
    nickname = generate_nickname(excluded)
    assert nickname not in excluded


def test_validate_nickname_format_valid():
    """Test validation of valid nicknames."""
    assert validate_nickname_format("happy_bright_forest")
    assert validate_nickname_format("swift_silver_mountain")
    assert validate_nickname_format("a_b_c")


def test_validate_nickname_format_invalid():
    """Test validation rejects invalid formats."""
    assert not validate_nickname_format("happy_bright")  # Only 2 parts
    assert not validate_nickname_format("happy_bright_forest_name")  # 4 parts
    assert not validate_nickname_format("happy__forest")  # Empty part
    assert not validate_nickname_format("happy bright forest")  # Wrong separator


def test_nickname_collision_handling():
    """Test handling of extremely rare collisions (with UUID fallback)."""
    # Generate many nicknames to test collision probability
    nicknames = set()
    for _ in range(50):
        nickname = generate_nickname()
        # All should be unique due to collision avoidance
        assert nickname not in nicknames
        nicknames.add(nickname)


def test_generate_many_nicknames():
    """Stress test: generate many unique nicknames."""
    nicknames = []
    excluded = set()
    
    for _ in range(100):
        nickname = generate_nickname(excluded)
        assert validate_nickname_format(nickname)
        assert nickname not in nicknames
        nicknames.append(nickname)
        excluded.add(nickname)
    
    # All 100 should be unique
    assert len(set(nicknames)) == 100
