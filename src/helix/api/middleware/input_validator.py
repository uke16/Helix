"""Input Validation Middleware for HELIX API.

ADR-035 Fix 2: Input validation to prevent abuse and ensure data integrity.

This module provides:
- Message size limits (100KB per message)
- Request size limits (100 messages per request)
- Role validation (only user, assistant, system allowed)

Usage:
    from helix.api.middleware import InputValidator

    # In your endpoint:
    InputValidator.validate_chat_request(request)
"""

from typing import TYPE_CHECKING

from fastapi import HTTPException

if TYPE_CHECKING:
    from ..models import ChatCompletionRequest


# === Configuration Constants ===

MAX_MESSAGE_LENGTH = 100_000  # 100KB per message
"""Maximum allowed length for a single message content in characters."""

MAX_MESSAGES_PER_REQUEST = 100
"""Maximum number of messages allowed in a single chat completion request."""

VALID_ROLES = {"user", "assistant", "system"}
"""Valid roles for chat messages per OpenAI API specification."""


class InputValidationError(HTTPException):
    """Custom exception for input validation failures.

    Extends HTTPException with status_code 400 (Bad Request).
    """

    def __init__(self, detail: str):
        super().__init__(status_code=400, detail=detail)


class InputValidator:
    """Validates incoming chat completion requests.

    ADR-035 Fix 2: Provides comprehensive input validation to prevent:
    - Resource exhaustion from oversized messages
    - Invalid role injection
    - Request flooding with excessive messages

    All validation methods are static and raise HTTPException on failure.
    """

    @staticmethod
    def validate_chat_request(request: "ChatCompletionRequest") -> None:
        """Validate a complete chat completion request.

        Performs all validation checks in sequence:
        1. Message count validation
        2. Per-message validation (role and content length)

        Args:
            request: The ChatCompletionRequest to validate.

        Raises:
            HTTPException: 400 error with descriptive message on validation failure.
        """
        InputValidator.validate_message_count(request.messages)

        for idx, msg in enumerate(request.messages):
            InputValidator.validate_message_role(msg.role, idx)
            InputValidator.validate_message_length(msg.content, idx)

    @staticmethod
    def validate_message_count(messages: list) -> None:
        """Validate the number of messages in a request.

        Args:
            messages: List of messages to check.

        Raises:
            HTTPException: If message count exceeds MAX_MESSAGES_PER_REQUEST.
        """
        if len(messages) > MAX_MESSAGES_PER_REQUEST:
            raise InputValidationError(
                f"Too many messages: {len(messages)}. "
                f"Maximum allowed: {MAX_MESSAGES_PER_REQUEST}"
            )

    @staticmethod
    def validate_message_role(role: str, message_index: int = 0) -> None:
        """Validate a message role.

        Args:
            role: The role string to validate.
            message_index: Index of the message (for error reporting).

        Raises:
            HTTPException: If role is not in VALID_ROLES.
        """
        if role not in VALID_ROLES:
            raise InputValidationError(
                f"Invalid role '{role}' in message {message_index}. "
                f"Valid roles: {', '.join(sorted(VALID_ROLES))}"
            )

    @staticmethod
    def validate_message_length(content: str, message_index: int = 0) -> None:
        """Validate message content length.

        Args:
            content: The message content to check.
            message_index: Index of the message (for error reporting).

        Raises:
            HTTPException: If content length exceeds MAX_MESSAGE_LENGTH.
        """
        if len(content) > MAX_MESSAGE_LENGTH:
            raise InputValidationError(
                f"Message {message_index} too long: {len(content)} characters. "
                f"Maximum allowed: {MAX_MESSAGE_LENGTH}"
            )

    @staticmethod
    def validate_model_name(model: str) -> None:
        """Validate model name format.

        Basic validation to prevent injection attacks via model name.

        Args:
            model: The model name to validate.

        Raises:
            HTTPException: If model name contains invalid characters.
        """
        # Model names should be alphanumeric with hyphens and underscores
        if not model:
            raise InputValidationError("Model name cannot be empty")

        # Simple validation: no path traversal or special characters
        forbidden_chars = {".", "/", "\\", "\n", "\r", "\t", "\0"}
        if any(char in model for char in forbidden_chars):
            raise InputValidationError(
                f"Invalid characters in model name: {model!r}"
            )

        # Reasonable length limit
        if len(model) > 256:
            raise InputValidationError(
                f"Model name too long: {len(model)} characters. Maximum: 256"
            )
