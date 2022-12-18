from dataclasses import dataclass, field
from enum import Enum


class UnavailabilityText(str, Enum):  # allow comparison with strings
    EN = 'Currently unavailable.'


class OptionPatterns(str, Enum):
    EN = r'[0-9]+ options? from '


@dataclass
class AmazonLocale():
    code: str
    domain: str
    unavailable_text: UnavailabilityText
    option_pattern: OptionPatterns
    child_asin: str
    parent_asin: str
    product_group: str

    def __hash__(self):
        return hash(self.code)


# requires valid child_asin, parent_asin, and product_group for item dimension endpoint
locale_list = [
    AmazonLocale('AU', 'www.amazon.com.au', UnavailabilityText.EN, OptionPatterns.EN,
                 'B08N3J8GTX', 'B0BCMPYWKN', 'amazon_ereaders_display_on_website'),
    AmazonLocale('SG', 'www.amazon.sg', UnavailabilityText.EN, OptionPatterns.EN,
                 'B09SWTG9GF', 'B0BCSYDF82', 'amazon_devices_display_on_website'),
    AmazonLocale('UK', 'www.amazon.co.uk', UnavailabilityText.EN, OptionPatterns.EN,
                 'B08N36XNTT', 'B0BF6HS47P', 'amazon_ereaders_display_on_website'),
]

default_locale = AmazonLocale('US', 'www.amazon.com', UnavailabilityText.EN, OptionPatterns.EN,
                              'B09TMK7QFX', 'B0BCTGXVB2', 'amazon_ereaders_display_on_website')

locale_list.append(default_locale)


def get_locale_data(country, logger):
    domain = next(
        locale_data for locale_data in locale_list if locale_data.code == country)

    if not domain:
        logger.info(f'Undefined country "{country}", defaulting to US')

    return domain if domain else \
        next(locale_data for locale_data in locale_list if locale_data.code == 'US')


def string_to_boolean(string):
    return string.lower().strip() in ['yes', 'true']


@dataclass
class QueryStatus():
    ok: bool = True
    errors: list[str] = field(default_factory=list)

    def refresh(self):
        self.ok = False if self.errors else True


@dataclass
class _BaseQuery():
    query: str
    status: QueryStatus
    locale: AmazonLocale = field(default=default_locale)
    country: str = 'US'

    def validate_country(self):
        if self.country:
            if not self.country.isalpha() or len(self.country) != 2:
                self.status.errors.append('Invalid country code')
            self.country = self.country.upper()

    def validate_locale(self):
        if self.country:
            self.locale = next(
                (locale for locale in locale_list if locale.code == self.country), default_locale)


@dataclass
class _PriceFilter():
    min_price: str = None
    max_price: str = None


@dataclass
class _BaseQueryWithPriceFilter(_PriceFilter, _BaseQuery):
    def validate_price_filters(self):
        if self.max_price and not self.max_price.isnumeric():
            self.status.errors.append('Invalid max price')

        if self.min_price and not self.min_price.isnumeric():
            self.status.errors.append('Invalid min price')


@dataclass
class _AmazonSearchFilter:
    strict: bool = False

    def validate_amazon_search_filters(self):
        if self.strict:
            self.strict = string_to_boolean(self.strict)


@dataclass
class AmazonSearchQuery(_AmazonSearchFilter, _BaseQueryWithPriceFilter):
    __slots__ = ['query', 'country', 'locale', 'min_price',
                 'max_price', 'strict']

    def __post_init__(self):
        if not isinstance(self.query, str):
            self.status.errors.append('Invalid query')

        self.validate_country()
        self.validate_locale()
        self.validate_price_filters()
        self.validate_amazon_search_filters()
        self.status.refresh()


@dataclass
class AmazonListQuery(_BaseQueryWithPriceFilter):
    __slots__ = ['query', 'country', 'locale', 'min_price', 'max_price']

    def __post_init__(self):
        if not isinstance(self.query, str):
            self.status.errors.append('Invalid id (ASIN)')

        self.validate_country()
        self.validate_locale()
        self.validate_price_filters()
        self.status.refresh()
