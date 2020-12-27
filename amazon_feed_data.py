from dataclasses import dataclass


@dataclass
class _PriceFilter:
    min_price: str = None
    max_price: str = None


@dataclass
class _BaseSearchQuery:
    query: str
    strict: bool = False


@dataclass
class _AmazonSearchFilter:
    country: str = 'US'
    buybox_only: bool = False


@dataclass
class AmazonSearchQuery(_PriceFilter, _AmazonSearchFilter, _BaseSearchQuery):
    __slots__ = ['query', 'strict', 'country',
                 'buybox_only', 'min_price', 'max_price']


@dataclass
class _BaseItemListing:
    id: str


@dataclass
class AmazonListQuery(_PriceFilter, _AmazonSearchFilter, _BaseItemListing):
    __slots__ = ['id', 'country', 'buybox_only' 'min_price', 'max_price']
