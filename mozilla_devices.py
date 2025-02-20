from enum import Enum
from amazon_feed_data import FeedConfig

CATALOG_URL = "https://code.cdn.mozilla.net/devices/devices.json"


class DeviceType(Enum):
    PHONES = "phones"
    TABLETS = "tablets"
    LAPTOPS = "laptops"
    TELEVISIONS = "televisions"

def get_useragent_list(device_type: DeviceType, config: FeedConfig) -> list[str]:
    config.logger.debug(f"Querying endpoint: {CATALOG_URL}")
    catalog_response = config.session.get(CATALOG_URL)
    catalog_json: dict = catalog_response.json() if catalog_response.ok else None

    if catalog_response.ok:
        useragent_list: list[str] = [
            device["userAgent"] for device in catalog_json[device_type.value]
        ]
        config.logger.info(
            f"Found {len(useragent_list)} user agents for {device_type.name.lower()}"
        )
        return useragent_list

    else:
        config.logger.warning("Unable to get useragent list.")
        return []
