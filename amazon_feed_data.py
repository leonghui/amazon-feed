from dataclasses import dataclass


@dataclass
class _PriceFilter:
    min_price: str = None
    max_price: str = None


@dataclass
class _BaseQuery:
    query: str
    country: str = 'US'


@dataclass
class _AmazonSearchFilter:
    strict: bool = False
    buybox_only: bool = False


@dataclass
class AmazonSearchQuery(_PriceFilter, _AmazonSearchFilter, _BaseQuery):
    __slots__ = ['query', 'country', 'strict',
                 'buybox_only', 'min_price', 'max_price']


@dataclass
class AmazonListQuery(_PriceFilter, _BaseQuery):
    __slots__ = ['query', 'country', 'min_price', 'max_price']
