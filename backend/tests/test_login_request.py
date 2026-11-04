import pytest
from pydantic import ValidationError

from app.application.auth_service import AccountRequest, LoginRequest


def test_login_request_accepts_legacy_password_under_12_characters():
    request = LoginRequest(email="user@example.com", password="OldPass1!")

    assert request.password == "OldPass1!"


def test_registration_request_still_requires_12_character_password():
    with pytest.raises(ValidationError):
        AccountRequest(
            email="user@example.com",
            password="OldPass1!",
            full_name="Test User",
        )


@pytest.mark.parametrize("password", ["", "á" * 37])
def test_login_request_rejects_empty_or_overlong_bcrypt_password(password):
    with pytest.raises(ValidationError):
        LoginRequest(email="user@example.com", password=password)
