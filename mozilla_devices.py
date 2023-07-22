from enum import Enum

CATALOG_URL = "https://code.cdn.mozilla.net/devices/devices.json"


class DeviceType(Enum):
    PHONES = "phones"
    TABLETS = "tablets"
    LAPTOPS = "laptops"
    TELEVISIONS = "televisions"


def get_useragent_list(device_type, config):
    config.logger.debug(f"Querying endpoint: {CATALOG_URL}")
    catalog_response = config.session.get(CATALOG_URL)
    catalog_json = catalog_response.json() if catalog_response.ok else None

    if catalog_response.ok:
        useragent_list = [
            device["userAgent"] for device in catalog_json[device_type.value]
        ]
        config.logger.info(
            f"Found {len(useragent_list)} user agents for {device_type.name.lower()}"
        )
        return useragent_list

    else:
        config.logger.warning("Unable to get useragent list.")
        return None
