from logging import Logger
from typing import Annotated

from curl_cffi import Session
from fastapi import Query
from pydantic import AfterValidator, BaseModel, Field

from models.amazon import AmazonLocale, default_locale
from models.validators import validate_asin, validate_country, validate_query_str


def string_to_boolean(string: str) -> bool:
    return string.lower().strip() in ["yes", "true"]


class QueryConfig(BaseModel):
    session: Session
    logger: Logger
    useragent: str

    class Config:
        arbitrary_types_allowed: bool = True


class QueryStatus(BaseModel):
    ok: bool = True
    errors: list[str] = []

    def refresh(self) -> None:
        self.ok = not self.errors


class _BaseQuery(BaseModel):
    status: QueryStatus
    config: QueryConfig
    query_str: str
    country: Annotated[str, AfterValidator(func=validate_country)] = "US"
    locale: Annotated[AmazonLocale, AfterValidator(func=validate_country)] = (
        default_locale
    )


class FilterableQuery(_BaseQuery):
    min_price: int | None = None
    max_price: int | None = None


class _AmazonKeywordFilter(BaseModel):
    strict: bool | None = False


class AmazonKeywordQuery(_AmazonKeywordFilter, FilterableQuery):
    query_str: Annotated[str, AfterValidator(func=validate_query_str)]


class AmazonAsinQuery(FilterableQuery):
    query_str: Annotated[str, AfterValidator(func=validate_asin)]


class QueryParams(BaseModel):
    q: str = Field(Query(..., description="Search query"))
    country: str = Field(Query("us", description="Country code"))
    min_price: int | None = Field(Query(None, description="Minimum price"))
    max_price: int | None = Field(Query(None, description="Maximum price"))
    strict: bool | None = Field(Query(False, description="Strict mode"))
