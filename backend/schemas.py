"""Pydantic Model Schemas"""

from functools import cached_property
from typing import Annotated, Any

from pydantic import BaseModel, BeforeValidator, StrictBool, computed_field

from backend.utils import generate_hash


class BaseFields(BaseModel):
    """Shared API data"""

    count: int
    next: str | None
    previous: str | None


class QueryResults(BaseModel):
    """Pokemon Element"""

    name: str
    url: str
    sprites: dict


class PokemonDetailed(BaseFields):
    """List of pokemon with sprites"""

    # Extends BaseFields
    results: list[QueryResults]


class Hosts(BaseModel):
    """Bundled API hosts descriptor."""

    data: str
    media: str


class RemoteError(BaseModel):
    """Defines standard for remote error messaging."""

    msg: str
    error: int


class SharesResponseParams(BaseModel):
    """Shared response params."""

    from_cache: StrictBool


class ResponseData(SharesResponseParams):
    """Defines remote api JSON response model."""

    headers: dict | None
    body: Any


class ResponseMedia(SharesResponseParams):
    """Defines remote api media response model."""

    headers: dict
    body: bytes


class ResponseHeaders(SharesResponseParams):
    """Defines headers return schema."""

    status_code: int
    is_success: StrictBool
    headers: dict


def process_query(raw_query: dict[str, int | None] | None) -> dict:
    """Process GET-params

    Requests omits params whose values are None.
    This is not supported by HTTPX. So we're doing it for HTTPX.
    """

    processed_query: dict = {}
    if raw_query:
        for data in raw_query:
            if raw_query[data] is not None:
                processed_query[data] = raw_query[data]

    return processed_query


class DataForRequest(BaseModel):
    """Defines params that can be used
    when making a request to remote API."""

    url: str
    query: Annotated[dict[str, int | None] | None, BeforeValidator(process_query)] = None
    headers: dict[str, str] | None = None

    @computed_field(description="Hash value calculated from `url` and `query`")
    @cached_property
    def hash_value(self) -> str:
        return generate_hash(self.url, 16, self.query)


class CreatedOutput(BaseModel):
    """Output created by `create_` function."""

    content: str
    source: list[str]

    @computed_field(description="Calculated etag of `content` field")
    @cached_property
    def etag(self) -> str:
        return generate_hash(self.content, 10)


class UnexpectedFunctionCallError(BaseException):
    """Function was called when it shouldn't've been."""

    msg: str
