from dataclasses import dataclass


@dataclass
class AmazonSearchQueryClass:
    query: str
    node_id: str
    country: str
    min_price: str = None
    max_price: str = None
    buybox_only: bool = False
    strict: bool = False