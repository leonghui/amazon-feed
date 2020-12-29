from requests import Session


CATALOG_URL = 'https://code.cdn.mozilla.net/devices/devices.json'


def get_phone_useragent_list(logger):
    logger.debug(f"Querying endpoint: {CATALOG_URL}")
    catalog_response = Session().get(CATALOG_URL)
    catalog_json = catalog_response.json() if catalog_response.ok else None

    if catalog_response.ok:
        useragent_list = [phone['userAgent']
                          for phone in catalog_json['phones']]
        logger.info(f"Found {len(useragent_list)} phone user agents.")
        return useragent_list

    else:
        logger.warning('Unable to get useragent list.')
        return None
