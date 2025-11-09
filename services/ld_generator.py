from pydantic.networks import HttpUrl

from models.amazon.asin import Asin
from models.json_ld import Offer, Product
from stockholm import Money


def generate_linked_data(
    base_url: str,
    item_id: str,
    item_price: Money | None,
    item_title: str | None = None,
    item_thumbnail_url: str | None = None,
) -> Product:
    if not item_price:
        item_offer: Offer = Offer(availability="https://schema.org/OutOfStock")
    else:
        item_offer = Offer(
            priceCurrency=item_price.currency_code, price=item_price.amount
        )

    product: Product = Product(
        asin=Asin(id=item_id),
        name=item_title,
        image=[HttpUrl(url=item_thumbnail_url)] if item_thumbnail_url else None,
        offers=item_offer,
    )

    return product


def get_html(feed_items: list[Product]) -> str:
    serialised_items = (
        "["
        + ",".join(
            [product.model_dump_json(exclude_none=True) for product in feed_items]
        )
        + "]"
    )

    html_text: str = f'<!DOCTYPE html><script type="application/ld+json">{serialised_items}</script><body>{serialised_items}</body></html>'
    return html_text
