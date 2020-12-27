from dataclasses import dataclass


def string_to_boolean(string):
    return string.lower().strip() in ['yes', 'true']


@dataclass
class QueryStatus():
    ok: bool
    errors: list[str]


@dataclass
class _BaseQuery():
    status: QueryStatus
    query: str = None
    country: str = 'US'

    def validateCountry(self):
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
    def validatePriceFilters(self):
        if self.max_price and not self.max_price.isnumeric():
            self.status.errors.append('Invalid max price')

        if self.min_price and not self.min_price.isnumeric():
            self.status.errors.append('Invalid min price')


@dataclass
class _AmazonSearchFilter:
    buybox_only: bool = False
    strict: bool = False

    def validateAmazonSearchFilters(self):
        if self.buybox_only:
            self.buybox_only = string_to_boolean(self.buybox_only)
        if self.strict:
            self.strict = string_to_boolean(self.strict)


@dataclass
class AmazonSearchQuery(_AmazonSearchFilter, _BaseQueryWithPriceFilter):
    __slots__ = ['query', 'country', 'min_price',
                 'max_price', 'buybox_only', 'strict']

    def __post_init__(self):
        self.validateCountry()
        self.validatePriceFilters()
        self.validateAmazonSearchFilters()

        if not isinstance(self.query, str):
            self.status.errors.append('Invalid query')

        if self.status.errors:
            self.status.ok = False


@dataclass
class AmazonListQuery(_BaseQueryWithPriceFilter):
    __slots__ = ['query', 'country', 'min_price', 'max_price']

    def __post_init__(self):
        super().validateCountry()
        super().validatePriceFilters()

        if not isinstance(self.query, str):
            self.status.errors.append('Invalid ASIN')

        if self.status.errors:
            self.status.ok = False
