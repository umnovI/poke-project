"""FastAPI dependencies"""

import math
import re
from asyncio import Lock
from hmac import compare_digest
from typing import Annotated

from fastapi import BackgroundTasks, Depends, HTTPException

from backend.api import fetch_headers, fetch_remote, fetch_remote_media
from backend.schemas import DataForRequest, RemoteError, ResponseData, ResponseHeaders, ResponseMedia
from backend.shared_config import HISHEL_CLIENT, HOST


async def make_request(
    endpoint: str,
    query: dict | None = None,
    backend: bool = False,
    background_tasks: BackgroundTasks | None = None,
) -> ResponseData:
    """Form a general request and send it to fetch function.

    Args:
        endpoint (str): endpoint name
        query (dict | None, optional): GET-query. Defaults to None.
        media (bool, optional): Is request made to get a media file? Defaults to False.
        backend (bool, optional): For backed usage. Doesn't perform hosts replacements.

    Raises:
        HTTPException: if remote API server responds with an error raising this error on our side

    Returns:
        dict: { body: {}, headers: {} }
    """

    if not backend:
        data = await fetch_remote(DataForRequest(url=endpoint, query=query), HISHEL_CLIENT, HOST, background_tasks)
    else:
        data = await fetch_remote(
            DataForRequest(url=endpoint, query=query), HISHEL_CLIENT, background_tasks=background_tasks
        )

    if isinstance(data, RemoteError):
        raise HTTPException(status_code=data.error, detail=data.msg)

    return data


async def make_media_request(
    endpoint: str,
) -> ResponseMedia:
    data = await fetch_remote_media(endpoint, HOST.media, client=HISHEL_CLIENT)

    if isinstance(data, RemoteError):
        raise HTTPException(status_code=data.error, detail=data.msg)

    return data


async def request_headers(url: str, query: dict | None = None, headers: dict | None = None) -> ResponseHeaders:
    """Return headers or raise an error.

    Args:
        url (str): requested endpoint
        headers (dict | None, optional): Headers to send with request. Defaults to None.

    Raises:
        HTTPException: If a server error.

    Returns:
        ResponseHeaders: Response headers.
    """

    data = await fetch_headers(DataForRequest(url=url, query=query, headers=headers), HOST.data, HISHEL_CLIENT)

    if isinstance(data, RemoteError):
        raise HTTPException(status_code=data.error, detail=data.msg)

    return data


async def etag_compare(if_none_match: str | None, headers: dict | None) -> None:
    """Compare etag

    Args:
        if_none_match (str | None): client's cached etag
        headers (dict): headers to send when 304 is thrown

    Raises:
        HTTPException: throw 304 if etag is matching
    """

    if if_none_match and headers and headers["etag"]:
        # Implementing rfc9110 https://www.rfc-editor.org/rfc/rfc9110#name-comparison-2
        compare: list[str] = []
        pattern = r'W/"(?P<value>.*)"'
        for item in (if_none_match, headers["etag"]):
            match = re.fullmatch(pattern, item, re.ASCII)
            if match is not None:
                compare.append(match.group("value"))
            else:
                compare.append(item.strip('"'))

        if compare_digest(compare[0], compare[1]):
            raise HTTPException(status_code=304, headers=headers)


async def pagination_formatter(
    offset: int | None = None,
    limit: int | None = None,
) -> dict[str, int | None]:
    return {"offset": offset, "limit": limit}


async def raise_httpexception(status_code: int, msg: str | None = None) -> None:
    """Raise HTTPException

    Args:
        status_code (int): Status code to return
        msg (str): Human-readable description

    Raises:
        HTTPException
    """

    raise HTTPException(status_code=status_code, detail=msg)


PaginationQuery = Annotated[dict[str, int | None], Depends(pagination_formatter)]


class Paginator:
    """This class handles pagination for lists."""

    def __init__(self, items: list, limit: int | None = None, offset: int | None = None) -> None:
        """Slice list based on pagination params.

        Args:
            items (list): list of items
            limit (int | None, optional): Limit. Defaults to None.
            offset (int | None, optional): Offset. Defaults to None.
        """

        self.__items = items
        self.__count: int = len(items)
        self.__limit: int | None = limit
        self.__offset: int | None = offset
        self.__pages: int = 1
        self.__cur_page: int = 1

    def _get_pages(self) -> int:
        """Get number of pages"""

        if self.__limit is not None and self.__count > self.__limit:
            self.__pages = math.ceil(self.__count / self.__limit)
            return self.__pages
        return self.__pages

    def get_count(self) -> int:
        """Count number of items in list"""

        return self.__count

    def paginate(self) -> list:
        """Return sliced list based on offset and limit"""

        pages = self._get_pages()
        if self.__offset and self.__limit:
            self.__cur_page = math.ceil(self.__offset / self.__limit) + 1
            print("Current page: ", self.__cur_page, "of ", pages)
            return self.__items[self.__offset : self.__limit + self.__offset]
        if self.__limit:
            print("Current page: ", self.__cur_page, "of ", pages)
            return self.__items[: self.__limit]
        return self.__items

    def has_next(self) -> bool:
        """Has next page?"""

        if self.__pages <= self.__cur_page:
            return False
        return True

    def generate_next(self) -> dict[str, int] | None:
        """Generate dict with params for the next page

        Returns:
            dict[str, int] | None: Return `None` if unable to generate.
        """

        if not self.__offset and self.__limit:
            offset = self.__limit
        elif self.__offset and self.__limit:
            offset = self.__offset + self.__limit
        else:
            return None

        return {"offset": offset, "limit": self.__limit}


lock1 = Lock()
lock2 = Lock()
