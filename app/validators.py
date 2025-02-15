import re
from pydantic import EmailStr


def email_validator(email: EmailStr):
    BLACKLISTED_DOMAINS = ["tempmail.com", "disposable.com"]
    MAX_EMAIL_LENGTH = 254  # RFC 5321
    MIN_EMAIL_LENGTH = 3

    # Check email length
    if len(email) > MAX_EMAIL_LENGTH:
        raise ValueError(f"Email must be less than {MAX_EMAIL_LENGTH} characters")
    if len(email) < MIN_EMAIL_LENGTH:
        raise ValueError(f"Email must be at least {MIN_EMAIL_LENGTH} characters")

    # Basic format validation using regex
    email_regex = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
    if not re.match(email_regex, email):
        raise ValueError("Invalid email format")

    # Check domain not blacklisted
    domain = email.split("@")[1].lower()
    if domain in BLACKLISTED_DOMAINS:
        raise ValueError("Email domain not allowed")

    return email.lower()
