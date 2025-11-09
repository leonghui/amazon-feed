from pydantic import ConfigDict, Field, PositiveFloat
from pydantic.main import BaseModel

from models.feed import JsonFeedItem, JsonFeedTopLevel, SerHttpUrl


class Thing(BaseModel):
    type: str = Field(default="Thing", serialization_alias="@type")

    model_config = ConfigDict(serialize_by_alias=True)


class Offer(Thing):
    type: str = Field(default="Offer", serialization_alias="@type")
    priceCurrency: str | None
    price: PositiveFloat | None
    availability: str | None = "https://schema.org/InStock"


class Product(Thing):
    type: str = Field(default="Product", serialization_alias="@type")
    context: str = Field(default="https://schema.org/", serialization_alias="@context")
    name: str | None
    asin: str | None
    image: list[SerHttpUrl] | None
    offers: Offer | None


class ExtendedJsonFeedItem(JsonFeedItem):
    # Product schema encapsulated in <script type="application/ld+json">
    _linked_data: str | None = None


class ExtendedJsonFeedTopLevel(JsonFeedTopLevel):
    items: list[JsonFeedItem | ExtendedJsonFeedItem]
