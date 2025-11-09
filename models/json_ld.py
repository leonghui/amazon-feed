from decimal import Decimal

from pydantic import ConfigDict, Field
from pydantic.main import BaseModel

from models.amazon.asin import Asin
from models.feed import SerHttpUrl


class Thing(BaseModel):
    type: str = Field(default="Thing", serialization_alias="@type")

    model_config = ConfigDict(serialize_by_alias=True)


class Offer(Thing):
    type: str = Field(default="Offer", serialization_alias="@type")
    priceCurrency: str | None = None
    price: Decimal | None = None
    availability: str | None = "https://schema.org/InStock"


class Product(Thing):
    type: str = Field(default="Product", serialization_alias="@type")
    context: str = Field(default="https://schema.org/", serialization_alias="@context")
    name: str | None
    asin: Asin | None
    image: list[SerHttpUrl] | None
    offers: Offer | None
