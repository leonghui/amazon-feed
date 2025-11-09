from stockholm import Money

from models.query import FilterableQuery


# Price validation and filtering
def validate_price(query: FilterableQuery, price_str: str) -> Money:
    price: Money = Money(
        amount=price_str.replace(query.locale.currency_sign, ""),
        currency_code=query.locale.currency_code,
    )
    return price
