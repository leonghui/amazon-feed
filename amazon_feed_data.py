from dataclasses import dataclass, field


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
    country: str = 'US'

    def validate_country(self):
        if self.country:
            if not self.country.isalpha() or len(self.country) != 2:
                self.status.errors.append('Invalid country code')
            self.country = self.country.upper()


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
    __slots__ = ['query', 'country', 'min_price',
                 'max_price', 'strict']

    def __post_init__(self):
        if not isinstance(self.query, str):
            self.status.errors.append('Invalid query')

        self.validate_country()
        self.validate_price_filters()
        self.validate_amazon_search_filters()
        self.status.refresh()


@dataclass
class AmazonListQuery(_BaseQueryWithPriceFilter):
    __slots__ = ['query', 'country', 'min_price', 'max_price']

    def __post_init__(self):
        if not isinstance(self.query, str):
            self.status.errors.append('Invalid id (ASIN)')

        self.validate_country()
        self.validate_price_filters()
        self.status.refresh()
