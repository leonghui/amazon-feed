from dataclasses import dataclass, field


@dataclass
class AmazonLocaleData():
    code: str
    domain: str
    child_asin: str
    parent_asin: str
    product_group: str


# requires valid child_asin, parent_asin, and product_group for item dimension endpoint
locale_list = [
    AmazonLocaleData('AU', 'www.amazon.com.au', 'B08F7PTF53',
                     'B08J926K2M', 'ce_display_on_website'),
    AmazonLocaleData('SG', 'www.amazon.sg', 'B08F7PTF53',
                     'B08J926K2M', 'video_games_display_on_website'),
]

default_locale = AmazonLocaleData('US', 'www.amazon.com', 'B08F7PTF53',
                                  'B08J926K2M', 'video_games_display_on_website')

locale_list.append(default_locale)


def get_locale_data(country, logger):
    domain = next(
        locale_data for locale_data in locale_list if locale_data.code == country)

    if not domain:
        logger.info(f'Undefined country "{country}", defaulting to US')

    return domain if domain else next(locale_data for locale_data in locale_list if locale_data.code == 'US')


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
    locale: AmazonLocaleData = default_locale
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
