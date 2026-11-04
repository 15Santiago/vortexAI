import pytest
from pydantic import ValidationError

from app.application.auth_service import ProfileUpdateRequest


def test_profile_request_allows_omitting_password():
    request = ProfileUpdateRequest(email="user@example.com", full_name="Test User")

    assert request.password is None


def test_profile_request_rejects_short_optional_password():
    with pytest.raises(ValidationError):
        ProfileUpdateRequest(
            email="user@example.com",
            full_name="Test User",
            password="short",
        )
