from pydantic import BaseModel


class AmazonLocale(BaseModel):
    code: str
    domain: str
    currency_sign: str
    currency_code: str


locale_list: list[AmazonLocale] = [
    AmazonLocale(
        code="AU", domain="www.amazon.com.au", currency_sign="$", currency_code="AUD"
    ),
    AmazonLocale(
        code="DE", domain="www.amazon.de", currency_sign="€", currency_code="EUR"
    ),
    AmazonLocale(
        code="ES", domain="www.amazon.es", currency_sign="€", currency_code="EUR"
    ),
    AmazonLocale(
        code="FR", domain="www.amazon.fr", currency_sign="€", currency_code="EUR"
    ),
    AmazonLocale(
        code="IT", domain="www.amazon.it", currency_sign="€", currency_code="EUR"
    ),
    AmazonLocale(
        code="SG", domain="www.amazon.sg", currency_sign="S$", currency_code="SGD"
    ),
    AmazonLocale(
        code="UK", domain="www.amazon.co.uk", currency_sign="£", currency_code="GBP"
    ),
    AmazonLocale(
        code="US", domain="www.amazon.com", currency_sign="$", currency_code="USD"
    ),
]

default_locale: AmazonLocale = next(
    locale for locale in locale_list if locale.code == "US"
)
