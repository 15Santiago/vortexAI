import unittest

from app.domain.password_policy import validate_password_strength


class PasswordPolicyTests(unittest.TestCase):
    def test_accepts_password_with_all_required_character_types(self):
        validate_password_strength("StrongPass123!")

    def test_rejects_password_without_uppercase(self):
        with self.assertRaisesRegex(ValueError, "mayúscula"):
            validate_password_strength("strongpass123!")

    def test_rejects_password_with_whitespace(self):
        with self.assertRaisesRegex(ValueError, "espacios"):
            validate_password_strength("Strong Pass123!")


if __name__ == "__main__":
    unittest.main()
