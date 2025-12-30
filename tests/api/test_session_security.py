"""Unit tests for Session Security (ADR-035).

Tests session ID generation and path sanitization to ensure
security against path traversal and session prediction attacks.

ADR-035 Fix 1: Cryptographically secure session IDs
ADR-035 Fix 5: Path traversal prevention
"""

import re
import tempfile
from pathlib import Path

import pytest

from helix.api.session_manager import SessionManager


@pytest.fixture
def temp_session_manager():
    """Create a SessionManager with a temporary directory."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield SessionManager(base_path=Path(tmpdir))


class TestPathSanitization:
    """Tests for _normalize_conversation_id() path traversal prevention."""

    def test_basic_alphanumeric(self, temp_session_manager):
        """Normal alphanumeric IDs should work unchanged."""
        result = temp_session_manager._normalize_conversation_id("abc123")
        assert result == "conv-abc123"

    def test_with_hyphens(self, temp_session_manager):
        """Hyphens should be preserved."""
        result = temp_session_manager._normalize_conversation_id("abc-123-def")
        assert result == "conv-abc-123-def"

    def test_path_traversal_double_dots(self, temp_session_manager):
        """Path traversal with .. should be blocked."""
        result = temp_session_manager._normalize_conversation_id("../../../etc/passwd")
        # Dots and slashes become hyphens, then consecutive hyphens collapsed
        assert ".." not in result
        assert "/" not in result
        # Result after sanitization: conv-etc-passwd
        assert "etc" in result
        assert "passwd" in result

    def test_path_traversal_backslash(self, temp_session_manager):
        """Windows-style path traversal should be blocked."""
        result = temp_session_manager._normalize_conversation_id("..\\..\\windows\\system32")
        assert ".." not in result
        assert "\\" not in result
        # Dots and backslashes become hyphens, then collapsed
        assert "windows" in result
        assert "system32" in result

    def test_mixed_traversal_attempt(self, temp_session_manager):
        """Mixed path traversal attempts should be blocked."""
        result = temp_session_manager._normalize_conversation_id("..//..\\../etc/passwd")
        assert ".." not in result
        assert "/" not in result
        assert "\\" not in result

    def test_special_characters_removed(self, temp_session_manager):
        """Special characters should be removed."""
        result = temp_session_manager._normalize_conversation_id("abc!@#$%^&*()_+=def")
        # Only alphanumeric and hyphens allowed
        assert re.match(r'^conv-[a-zA-Z0-9-]+$', result)
        assert "abc" in result
        assert "def" in result

    def test_underscores_converted_to_hyphens(self, temp_session_manager):
        """Underscores should be converted to hyphens."""
        result = temp_session_manager._normalize_conversation_id("abc_123_def")
        assert "_" not in result
        # Underscores become hyphens, consecutive hyphens are collapsed
        assert result == "conv-abc-123-def"

    def test_length_limit(self, temp_session_manager):
        """IDs should be limited to 64 characters total."""
        long_id = "a" * 100
        result = temp_session_manager._normalize_conversation_id(long_id)
        assert len(result) <= 64

    def test_empty_input_fallback(self, temp_session_manager):
        """Empty input should return fallback value."""
        result = temp_session_manager._normalize_conversation_id("")
        assert result == "conv-session"

    def test_only_special_chars_fallback(self, temp_session_manager):
        """Input with only special characters should return fallback."""
        result = temp_session_manager._normalize_conversation_id("!@#$%^&*()")
        assert result == "conv-session"

    def test_only_dots_fallback(self, temp_session_manager):
        """Input with only dots should return fallback."""
        result = temp_session_manager._normalize_conversation_id("......")
        assert result == "conv-session"

    def test_null_bytes_removed(self, temp_session_manager):
        """Null bytes should be removed."""
        result = temp_session_manager._normalize_conversation_id("abc\x00def")
        assert "\x00" not in result
        # Null bytes become hyphens, result is "conv-abc-def"
        assert "abc" in result
        assert "def" in result

    def test_newlines_removed(self, temp_session_manager):
        """Newlines should be removed."""
        result = temp_session_manager._normalize_conversation_id("abc\ndef\rend")
        assert "\n" not in result
        assert "\r" not in result

    def test_spaces_removed(self, temp_session_manager):
        """Spaces should be converted to hyphens."""
        result = temp_session_manager._normalize_conversation_id("abc def ghi")
        assert " " not in result
        # Spaces become hyphens
        assert result == "conv-abc-def-ghi"

    def test_consecutive_hyphens_collapsed(self, temp_session_manager):
        """Multiple consecutive hyphens should be collapsed to one."""
        result = temp_session_manager._normalize_conversation_id("abc---def")
        assert "---" not in result
        assert result == "conv-abc-def"

    def test_leading_trailing_hyphens_stripped(self, temp_session_manager):
        """Leading and trailing hyphens should be stripped."""
        result = temp_session_manager._normalize_conversation_id("-abc-def-")
        # Leading/trailing hyphens stripped from the inner part
        assert result == "conv-abc-def"
        # Result should not have extra hyphens at start/end after prefix
        assert not result.endswith("-")

    def test_unicode_characters_removed(self, temp_session_manager):
        """Unicode characters should be converted to hyphens."""
        result = temp_session_manager._normalize_conversation_id("abc\u00e9\u00f1def")
        # Non-ASCII chars become hyphens
        assert "\u00e9" not in result
        assert "\u00f1" not in result
        # Result contains the ASCII parts
        assert "abc" in result
        assert "def" in result

    def test_filesystem_safe_result(self, temp_session_manager):
        """Result should be safe for filesystem use."""
        # Test various dangerous inputs
        dangerous_inputs = [
            "../../../etc/passwd",
            "..\\..\\windows\\system32",
            "con",  # Windows reserved name
            "nul",  # Windows reserved name
            "file.txt",  # Dots
            "<script>alert</script>",
            "'; DROP TABLE sessions; --",
        ]
        for dangerous in dangerous_inputs:
            result = temp_session_manager._normalize_conversation_id(dangerous)
            # Result should only contain safe characters
            assert re.match(r'^conv-[a-zA-Z0-9-]+$', result) or result == "conv-session"
            # Result should not contain path separators
            assert "/" not in result
            assert "\\" not in result
            assert ".." not in result


class TestSessionIdGeneration:
    """Tests for cryptographically secure session ID generation."""

    def test_session_id_format(self, temp_session_manager):
        """Session IDs should have correct format."""
        session_id = temp_session_manager._generate_session_id()
        assert session_id.startswith("session-")
        # UUID4 hex is 32 characters
        assert len(session_id) == len("session-") + 32

    def test_session_ids_are_unique(self, temp_session_manager):
        """Generated session IDs should be unique."""
        ids = {temp_session_manager._generate_session_id() for _ in range(100)}
        assert len(ids) == 100

    def test_session_id_is_random(self, temp_session_manager):
        """Session IDs should not be derived from predictable sources."""
        # Generate two IDs - they should be different
        id1 = temp_session_manager._generate_session_id()
        id2 = temp_session_manager._generate_session_id()
        assert id1 != id2

    def test_session_id_only_hex_chars(self, temp_session_manager):
        """Session ID suffix should only contain hex characters."""
        session_id = temp_session_manager._generate_session_id()
        suffix = session_id.replace("session-", "")
        assert all(c in "0123456789abcdef" for c in suffix)


class TestGetOrCreateSessionSecurity:
    """Tests for session creation with security features."""

    def test_conversation_id_sanitized(self, temp_session_manager):
        """Conversation IDs should be sanitized before use."""
        # Attempt path traversal via conversation_id
        session_id, state = temp_session_manager.get_or_create_session(
            first_message="Test",
            conversation_id="../../../etc/passwd"
        )
        # Session should be created with sanitized ID
        assert ".." not in session_id
        assert "/" not in session_id
        assert temp_session_manager.session_exists(session_id)

    def test_random_session_id_without_conversation_id(self, temp_session_manager):
        """Sessions without conversation_id should get random IDs."""
        session_id1, _ = temp_session_manager.get_or_create_session(
            first_message="Same message"
        )
        session_id2, _ = temp_session_manager.get_or_create_session(
            first_message="Same message"
        )
        # ADR-035: Same message should get different session IDs (random)
        assert session_id1 != session_id2
        # Both should be UUID-based
        assert session_id1.startswith("session-")
        assert session_id2.startswith("session-")

    def test_session_path_is_within_base(self, temp_session_manager):
        """Session paths should always be within base_path."""
        # Try various traversal attacks
        attacks = [
            "../../../etc/passwd",
            "..\\..\\windows\\system32",
            "/absolute/path",
            "\\\\network\\share",
        ]
        for attack in attacks:
            session_id, _ = temp_session_manager.get_or_create_session(
                first_message="Test",
                conversation_id=attack
            )
            session_path = temp_session_manager.get_session_path(session_id)
            # Resolve to catch symlink shenanigans
            resolved = session_path.resolve()
            base_resolved = temp_session_manager.base_path.resolve()
            # Session path should be inside base_path
            assert str(resolved).startswith(str(base_resolved))


class TestSessionManagerConstants:
    """Tests for security-related constants."""

    def test_max_conversation_id_length_defined(self, temp_session_manager):
        """MAX_CONVERSATION_ID_LENGTH should be defined and reasonable."""
        assert hasattr(temp_session_manager, 'MAX_CONVERSATION_ID_LENGTH')
        assert temp_session_manager.MAX_CONVERSATION_ID_LENGTH == 64

    def test_lock_timeout_defined(self, temp_session_manager):
        """LOCK_TIMEOUT should be defined."""
        assert hasattr(temp_session_manager, 'LOCK_TIMEOUT')
        assert temp_session_manager.LOCK_TIMEOUT == 5
