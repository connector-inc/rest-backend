from pydantic import EmailStr, validate_email


def email_validator(email: EmailStr):
    _, normalized_email = validate_email(email.lower())

    BLACKLISTED_DOMAINS = ["tempmail.com", "disposable.com"]
    domain = normalized_email.split("@")[1]
    if domain in BLACKLISTED_DOMAINS:
        raise ValueError("Email domain not allowed")

    return email
