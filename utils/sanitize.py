import nh3

from config.constants import ALLOWED_ATTRIBUTES, ALLOWED_TAGS


def sanitize_html(
    html: str,
    allowed_tags: set[str] | None = ALLOWED_TAGS,
    allowed_attributes: dict[str, set[str]] | None = ALLOWED_ATTRIBUTES,
) -> str:
    # Sanitize HTML, restoring ampersands
    sanitized: str = nh3.clean(
        html=html, tags=allowed_tags, attributes=allowed_attributes
    ).replace("&amp;", "&")

    return sanitized
