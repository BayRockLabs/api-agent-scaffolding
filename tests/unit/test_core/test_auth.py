"""Unit tests for authentication"""

import pytest
from app.core.auth import UserContext, validate_user_context, UserRole


@pytest.mark.unit
class TestUserContext:
    def test_user_context_creation(self):
        """Test creating user context"""
        user = UserContext(
            user_id="test_123",
            email="test@example.com",
            role="analyst",
        )

        assert user.user_id == "test_123"
        assert user.email == "test@example.com"
        assert user.role == "analyst"

    def test_has_role(self):
        """Test role checking"""
        user = UserContext(user_id="1", email="test@test.com", role="admin")

        assert user.has_role("admin") is True
        assert user.has_role("user") is False

    def test_is_admin(self):
        """Test admin check"""
        admin = UserContext(user_id="1", email="admin@test.com", role=UserRole.ADMIN.value)
        user = UserContext(user_id="2", email="user@test.com", role=UserRole.ANALYST.value)

        assert admin.is_admin() is True
        assert user.is_admin() is False

    def test_validate_user_context_success(self):
        """Test user context validation"""
        user = validate_user_context(
            user_id="test_123",
            email="test@example.com",
            role="analyst",
        )

        assert user.user_id == "test_123"
        assert user.email == "test@example.com"

    def test_validate_user_context_missing_fields(self):
        """Test validation fails with missing fields"""
        with pytest.raises(ValueError):
            validate_user_context(user_id=None, email="test@example.com")

        with pytest.raises(ValueError):
            validate_user_context(user_id="test_123", email=None)
