import logging

from stockholm import ConversionError, Money

from models.query import FilterableQuery


# Price validation and filtering
def validate_price(query: FilterableQuery, price_str: str) -> Money:
    try:
        price: Money = Money(
            amount=price_str.replace(query.locale.currency_sign, ""),
            currency_code=query.locale.currency_code,
        )
    except ConversionError as e:
        logging.error(msg=f"Falling back to default conversion: {e}")
        price = Money(amount=query)

    return price
