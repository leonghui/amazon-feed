from pydantic import BaseModel


class AmazonLocale(BaseModel):
    code: str
    domain: str
    currency: str


locale_list: list[AmazonLocale] = [
    AmazonLocale(code="AU", domain="www.amazon.com.au", currency="$"),
    AmazonLocale(code="DE", domain="www.amazon.de", currency="€"),
    AmazonLocale(code="ES", domain="www.amazon.es", currency="€"),
    AmazonLocale(code="FR", domain="www.amazon.fr", currency="€"),
    AmazonLocale(code="IT", domain="www.amazon.it", currency="€"),
    AmazonLocale(code="SG", domain="www.amazon.sg", currency="S$"),
    AmazonLocale(
        code="UK",
        domain="www.amazon.co.uk",
        currency="£",
    ),
    AmazonLocale(
        code="US",
        domain="www.amazon.com",
        currency="$",
    ),
]

default_locale: AmazonLocale = next(
    locale for locale in locale_list if locale.code == "US"
)
