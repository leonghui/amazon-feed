import re
from dataclasses import dataclass, field
from logging import Logger
from typing import override

from curl_cffi import Session

ASIN_PATTERN = r"^(B[\dA-Z]{9}|\d{9}(X|\d))$"


@dataclass
class AmazonLocale:
    code: str
    domain: str
    currency: str

    @override
    def __hash__(self) -> int:
        return hash(self.code)


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
]

default_locale: AmazonLocale = AmazonLocale(
    code="US",
    domain="www.amazon.com",
    currency="$",
)

locale_list.append(default_locale)


def string_to_boolean(string: str) -> bool:
    return string.lower().strip() in ["yes", "true"]


@dataclass()
class QueryConfig:
    session: Session
    logger: Logger
    useragent: str


@dataclass
class QueryStatus:
    ok: bool = True
    errors: list[str] = field(default_factory=list)

    def refresh(self) -> None:
        self.ok = False if self.errors else True


@dataclass
class _BaseQuery:
    status: QueryStatus
    config: QueryConfig
    query_str: str
    country: str = "US"
    locale: AmazonLocale = field(default=default_locale)

    def validate_country(self) -> None:
        if self.country:
            if not self.country.isalpha() or len(self.country) != 2:
                self.status.errors.append("Invalid country code")
            self.country = self.country.upper()

    def validate_locale(self) -> None:
        if self.country:
            self.locale = next(
                (locale for locale in locale_list if locale.code == self.country),
                default_locale,
            )


@dataclass
class _PriceFilter:
    min_price: str = ""
    max_price: str = ""


@dataclass
class FilterableQuery(_PriceFilter, _BaseQuery):
    def validate_price_filters(self) -> None:
        if self.max_price and not self.max_price.isnumeric():
            self.status.errors.append("Invalid max price")

        if self.min_price and not self.min_price.isnumeric():
            self.status.errors.append("Invalid min price")


@dataclass
class _AmazonKeywordFilter:
    strict_str: str = "False"
    strict: bool = False

    def validate_amazon_search_filters(self) -> None:
        if self.strict_str:
            self.strict = string_to_boolean(string=self.strict_str)


@dataclass
class AmazonKeywordQuery(_AmazonKeywordFilter, FilterableQuery):
    query_str: str

    def __post_init__(self) -> None:
        if not self.query_str:
            self.status.errors.append("Invalid query")

        self.validate_country()
        self.validate_locale()
        self.validate_price_filters()
        self.validate_amazon_search_filters()
        self.status.refresh()


@dataclass
class AmazonAsinQuery(FilterableQuery):
    query_str: str

    def __post_init__(self) -> None:
        if not re.match(ASIN_PATTERN, self.query_str):
            self.status.errors.append("Invalid id (ASIN)")

        self.validate_country()
        self.validate_locale()
        self.validate_price_filters()
        self.status.refresh()
