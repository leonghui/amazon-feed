import re
from dataclasses import dataclass, field
from logging import Logger
from typing import override

from requests_cache import CachedSession

ASIN_PATTERN = r"^(B[\dA-Z]{9}|\d{9}(X|\d))$"
BOT_PATTERN = r"automated access|captcha"


@dataclass
class AmazonLocale:
    code: str
    domain: str
    currency: str

    @override
    def __hash__(self):
        return hash(self.code)


locale_list = [
    AmazonLocale("AU", "www.amazon.com.au", "$"),
    AmazonLocale("SG", "www.amazon.sg", "S$"),
    AmazonLocale(
        "UK",
        "www.amazon.co.uk",
        "£",
    ),
]

default_locale = AmazonLocale(
    "US",
    "www.amazon.com",
    "$",
)

locale_list.append(default_locale)


def string_to_boolean(string: str):
    return string.lower().strip() in ["yes", "true"]


@dataclass()
class FeedConfig:
    session: CachedSession
    logger: Logger
    useragent: str = ""


@dataclass
class QueryStatus:
    ok: bool = True
    errors: list[str] = field(default_factory=list)

    def refresh(self):
        self.ok = False if self.errors else True


@dataclass
class _BaseQuery:
    status: QueryStatus
    config: FeedConfig
    query_str: str
    country: str = "US"
    locale: AmazonLocale = field(default=default_locale)

    def validate_country(self):
        if self.country:
            if not self.country.isalpha() or len(self.country) != 2:
                self.status.errors.append("Invalid country code")
            self.country = self.country.upper()

    def validate_locale(self):
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
class _BaseQueryWithPriceFilter(_PriceFilter, _BaseQuery):
    def validate_price_filters(self):
        if self.max_price and not self.max_price.isnumeric():
            self.status.errors.append("Invalid max price")

        if self.min_price and not self.min_price.isnumeric():
            self.status.errors.append("Invalid min price")


@dataclass
class _AmazonSearchFilter:
    strict_str: str = "False"
    strict: bool = False

    def validate_amazon_search_filters(self):
        if self.strict_str:
            self.strict = string_to_boolean(self.strict_str)


@dataclass
class AmazonListingQuery(_AmazonSearchFilter, _BaseQueryWithPriceFilter):
    query_str: str = "AMD"

    def from_item_query(self):
        assert isinstance(self, AmazonItemQuery)

        listing_query = AmazonListingQuery(
            status=self.status,
            query_str=self.query_str,
            config=self.config,
            country=self.country,
            min_price=self.min_price,
            max_price=self.max_price,
            strict_str="true",
        )

        return listing_query

    def __post_init__(self):
        if not self.query_str:
            self.status.errors.append("Invalid query")

        self.validate_country()
        self.validate_locale()
        self.validate_price_filters()
        self.validate_amazon_search_filters()
        self.status.refresh()


@dataclass
class AmazonItemQuery(_BaseQueryWithPriceFilter):
    query_str: str = "B08166SLDF"  #  AMD Ryzen 5 5600X Processor

    def __post_init__(self):
        if not re.match(ASIN_PATTERN, self.query_str):
            self.status.errors.append("Invalid id (ASIN)")

        self.validate_country()
        self.validate_locale()
        self.validate_price_filters()
        self.status.refresh()
