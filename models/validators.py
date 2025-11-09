import re

from models.amazon.locale import AmazonLocale, locale_list

ASIN_PATTERN = r"^(B[\dA-Z]{9}|\d{9}(X|\d))$"


def validate_country(value: str) -> str:
    if value and (not value.isalpha() or len(value) != 2):
        raise ValueError("Invalid country code")

    return value.upper()


def convert_to_locale(value: str) -> AmazonLocale:
    country_code: str = value

    return next((locale for locale in locale_list if locale.code == country_code))


def validate_query_str(value: str) -> str:
    if value and not len(value):
        raise ValueError("Invalid query")
    return value


def validate_asin(value: str) -> str:
    if not re.match(ASIN_PATTERN, value):
        raise ValueError("Invalid id (ASIN)")
    return value
