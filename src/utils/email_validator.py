from email_validator import validate_email, EmailNotValidError

def validate_email_address(email):
    try:
        valid = validate_email(email)
        return valid.email
    except EmailNotValidError as e:
        return str(e)
