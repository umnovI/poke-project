"""Remote API calls handler"""

import base64
import re
import time
from datetime import datetime
from urllib.parse import urlencode

import hishel
import ujson
from fastapi import BackgroundTasks, HTTPException
from httpx import Headers
from sqlmodel import Session as SQLSession

from backend.common import b64d, b64e
from backend.db_config import TPartialContent, db_engine
from backend.schemas import DataForRequest, Hosts, RemoteError, ResponseData, ResponseHeaders, ResponseMedia


async def headers_filter(headers: Headers, expected_headers: list[str]) -> dict | None:
    """Check if headers exist in remote API response

    Args:
        headers (Headers): API-response headers
        expected_headers (list[str]): headers expected to return to client

    Returns:
        dict | None: headers or none if headers were not found
    """

    return_headers: dict | None = {}
    for resp_header in expected_headers:
        if resp_header in headers:
            return_headers[resp_header] = headers[resp_header]

    if len(return_headers) == 0:  # pragma: no cover
        return_headers = None
    return return_headers


async def db_get(req: DataForRequest) -> str | None:
    """Get data from database.

    Args:
        req (DataForRequest): Data you're sending with request.

    Returns:
        str | None: Database contents or None if not found.
    """

    with SQLSession(db_engine) as session:
        item = session.get(TPartialContent, req.hash_value)
        if item:
            return b64d(item.content)
    return None


async def db_put(req: DataForRequest, body: str) -> None:
    """Look for cached data in database.
    If nothing found--add data.

    Args:
        req (DataForRequest): Data used to send a request to remote API
        body (str): Modified response from remote API you want to save.
    """

    source: str = req.url if not req.query else req.url + "?" + urlencode(query=req.query)

    with SQLSession(db_engine) as session:
        item = session.get(TPartialContent, req.hash_value, with_for_update=True)
        if item:
            item.content = b64e(body)
            item.updated = datetime.now()
            to_add = item
        else:
            to_add = TPartialContent(
                id=req.hash_value,
                content=b64e(body),
                created=datetime.now(),
                source=source,
            )
        session.add(to_add)
        session.commit()


async def format_links(response: str, host: str, api_media_url: str) -> str:
    """Remove host data from returned urls
       and make them relative. Plus encode media urls.

    Args:
        response (str): response data
        api_url (str): url we need to remove
        api_media_url (str): url we need to remove for media files

    Returns:
        str: mutated response with relative and encoded urls
    """

    # Delete host-specific info from body
    response = response.replace(host, "/api")
    media_url_search_pattern = r"\"" + re.escape(api_media_url) + r"(.+?\.[a-zA-Z]+)\""

    # this is an expensive operation (21ms server response time from 7ms before) / 17ms after cache implementation
    def encode_media_url(match: re.Match[str]) -> str:
        return '"' + "/api/media/?f=" + base64.urlsafe_b64encode(match.group(1).encode("utf-8")).decode("utf-8") + '"'

    response = re.sub(media_url_search_pattern, encode_media_url, response)
    return response


# IMPORTANT: IF RESPONSE TIME RAISES TO 200+MS CHECK `HISHEL`
async def fetch_remote(
    req: DataForRequest,
    client: hishel.AsyncCacheClient,
    hosts: Hosts | None = None,
    background_tasks: BackgroundTasks | None = None,
) -> RemoteError | ResponseData:
    """Fetch data from remote API-server.

    Args:
        req (DataForRequest): request data.
        client (AsyncCacheClient): hishel cache client
        hosts: (Hosts | None): Host urls. Defaults to None.

    Returns:
       RemoteError | ResponseData
    """

    if client:
        request_url: str = req.url
        if hosts and hosts.data:
            request_url = hosts.data + req.url

        print("Requesting body..", request_url, req.query)

        start = time.time()
        response = await client.get(request_url, timeout=3, params=req.query)
        end = time.time()
        print("Elapsed time during client.get: ", end - start)
        print(response.elapsed)
        if not response.is_success:
            return RemoteError(
                msg=f"Error {response.status_code} occurred while requesting {request_url}",
                error=response.status_code,
            )

        print("From cache:", response.extensions["from_cache"])
        response_body: dict = response.json()
        if "results" in response_body and not response_body["results"]:
            raise HTTPException(404, "Nothing was found")

        if (hosts and hosts.data and hosts.media) and background_tasks:
            if response.extensions["from_cache"]:
                db_body = await db_get(req)
                if db_body:
                    response_body = ujson.loads(db_body)
                else:
                    response_str = await format_links(
                        ujson.dumps(response_body, escape_forward_slashes=False), hosts.data, hosts.media
                    )
                    background_tasks.add_task(db_put, req, response_str)
                    response_body = ujson.loads(response_str)
            else:
                response_str = await format_links(
                    ujson.dumps(response_body, escape_forward_slashes=False), hosts.data, hosts.media
                )
                background_tasks.add_task(db_put, req, response_str)
                response_body = ujson.loads(response_str)

        # Headers expected to return in server response
        return_headers: list = [
            "cache-control",
            "age",
            "etag",
        ]
        return ResponseData(
            body=response_body,
            headers=await headers_filter(response.headers, return_headers),
            from_cache=response.extensions["from_cache"],
        )

    raise ValueError("Client is not defined.")  # pragma: no cover


async def fetch_remote_media(url: str, host: str, client: hishel.AsyncCacheClient) -> RemoteError | ResponseMedia:
    """Fetch media data

    Args:
        url (str): File URL
        api_url (str): Remote api address
        client (hishel.AsyncCacheClient): hishel client

    Raises:
        ValueError: if client is not defined

    Returns:
        ResponseMedia | RemoteError
    """

    if client:
        request_url = host + url
        response = await client.get(request_url, timeout=3)

        if not response.is_success:
            return RemoteError(
                msg=f"Error {response.status_code} occurred while requesting media file.",
                error=response.status_code,
            )

        return_headers: list = [
            "content-type",
            "etag",
            "cache-control",
            "age",
        ]
        headers = await headers_filter(response.headers, return_headers)
        if headers and "content-type" in headers:
            return ResponseMedia(
                body=response.content,
                headers=headers,
                from_cache=response.extensions["from_cache"],
            )
        raise TypeError("Remote API did not return content-type header.")  # pragma: no cover

    raise ValueError("Client is not defined.")  # pragma: no cover


async def fetch_headers(
    req: DataForRequest, host: str, client: hishel.AsyncCacheClient
) -> ResponseHeaders | RemoteError:
    """Fetch headers from remote API

    Args:
        req (DataForRequest): Data to make a request.
        host (str): Host to make request to.
        client (hishel.AsyncCacheClient): Hishel client.

    Raises:
        ValueError: If `client` not defined.

    Returns:
        ResponseHeaders | RemoteError: Headers from remote API or Error details.
    """

    if client:
        request_url = host + req.url
        print("Requesting headers..", request_url, req.query)
        response = await client.head(request_url, params=req.query, headers=req.headers, timeout=3)

        if response.is_client_error or response.is_server_error:
            return RemoteError(
                msg=f"Error {response.status_code} occurred while requesting {request_url}",
                error=response.status_code,
            )

        return ResponseHeaders(
            status_code=response.status_code,
            is_success=response.is_success,
            headers=dict(response.headers),
            from_cache=response.extensions["from_cache"],
        )

    raise ValueError("Client is not defined.")  # pragma: no cover
