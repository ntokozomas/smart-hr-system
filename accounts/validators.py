"""NFR-06: passwords need at least 8 characters with letters and numbers."""

from django.core.exceptions import ValidationError


class LettersAndNumbersValidator:
    """Reject passwords that do not contain at least one letter and one digit."""

    message = "Your password must contain at least one letter and one number."

    def validate(self, password, user=None):
        has_letter = any(ch.isalpha() for ch in password)
        has_digit = any(ch.isdigit() for ch in password)
        if not (has_letter and has_digit):
            raise ValidationError(self.message, code="password_letters_and_numbers")

    def get_help_text(self):
        return self.message
