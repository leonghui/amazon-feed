ITEM_QUANTITY = 1
STREAM_DELIMITER = "&&&"  # application/json-amazonui-streaming

ALLOWED_TAGS: set[str] = {"a", "img", "p"}
ALLOWED_ATTRIBUTES: dict[str, set[str]] = {"a": {"href", "title"}, "img": {"src"}}

HEADERS: dict[str, str] = {
    "Accept": "text/html,*/*",
    "Accept-Language": "en-US,en;q=0.5",
    "Accept-Encoding": "gzip, deflate, br, zstd",
    "X-Requested-With": "XMLHttpRequest",
    "Connection": "keep-alive",
    "device-memory": "8",
    "downlink": "9.3",
    "dpr": "2",
    "ect": "4g",
    "rtt": "0",
    "sec-ch-device-memory": "8",
    "sec-ch-dpr": "2",
    "sec-ch-ua": '"Chromium";v="128", "Not;A=Brand";v="24", "Android WebView";v="128"',
    "sec-ch-ua-mobile": "?1",
    "sec-ch-ua-platform": '"Android"',
    "sec-ch-ua-platform-version": '""',
    "sec-ch-viewport-width": "393",
    "Sec-Fetch-Dest": "empty",
    "Sec-Fetch-Mode": "cors",
    "Sec-Fetch-Site": "same-origin",
    "viewport-width": "393",
}

DEFAULT_USER_AGENT = "Amazon.com/30.4.0.100 (Android/14/Pixel 8a)"