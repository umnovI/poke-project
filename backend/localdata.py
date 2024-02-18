"""Mutate data from remote API and put them locally."""

from asyncio import Task, TaskGroup
from copy import deepcopy
from datetime import datetime, timedelta
from urllib.parse import urlencode

import ujson
from httpx import codes as status_code
from sqlalchemy.orm import selectinload
from sqlmodel import Session as SQLSession
from sqlmodel import select

from backend.api import format_links
from backend.common import b64d, b64e, generate_hash
from backend.db_config import TContent, THeaders, TRequestedURL, db_engine
from backend.dependencies import lock1, lock2, make_request, raise_httpexception, request_headers
from backend.schemas import CreatedOutput, DataForRequest, PokemonDetailed, ResponseData
from backend.shared_config import CACHE_TTL, HOST


# NOTE: 600 ms response time (no cache)
async def create_pokemon_detailed(endpoint: str, query: dict | None = None) -> CreatedOutput:
    """Create list of pokemon with their corresponding sprites."""

    source: list[str] = []
    poke_list = await make_request(HOST.data + endpoint, query=query, backend=True)
    source.append(HOST.data + endpoint if not query else HOST.data + endpoint + "?" + urlencode(query=query))

    poke_list_detailed = deepcopy(poke_list.body)
    remote_requests: list[Task[ResponseData]] = []

    try:
        async with TaskGroup() as tg:
            for pokemon in poke_list.body["results"]:
                remote_requests.append(tg.create_task(make_request(pokemon["url"], backend=True)))
                source.append(pokemon["url"])
    except ExceptionGroup:  # pragma: no cover
        print(list(result.result() for result in remote_requests))
        await raise_httpexception(500, "Internal Server Error")

    for idx, result in enumerate(remote_requests):
        poke_list_detailed["results"][idx]["sprites"] = result.result().body["sprites"]

    # Replace hosts and encode media urls
    poke_list_detailed = await format_links(
        ujson.dumps(poke_list_detailed, escape_forward_slashes=False), HOST.data, HOST.media
    )
    # Build next/prev links correctly
    poke_list_detailed = PokemonDetailed.model_validate_json(poke_list_detailed)
    if poke_list_detailed.next is not None:
        poke_list_detailed.next = poke_list_detailed.next.replace("/api/pokemon/", "/api/pokemon-detailed/")
    if poke_list_detailed.previous is not None:
        poke_list_detailed.previous = poke_list_detailed.previous.replace("/api/pokemon/", "/api/pokemon-detailed/")

    return CreatedOutput(content=poke_list_detailed.model_dump_json(), source=source)


async def create_search_list(endpoint: str, _: dict | None = None) -> CreatedOutput:
    # Request to check count value
    response = await make_request(HOST.data + endpoint, query={"limit": 1}, backend=True)
    count: int = response.body["count"]
    query: dict = {"limit": count}
    # Request all data
    response = await make_request(HOST.data + endpoint, query=query, backend=True)
    data: str = await format_links(ujson.dumps(response.body, escape_forward_slashes=False), HOST.data, HOST.media)

    return CreatedOutput(
        content=data,
        source=[HOST.data + endpoint + "?" + urlencode(query=query)],
    )


async def is_source_modified(endpoint: str, ehash: str, query: dict | None = None) -> bool:
    """Check if remote source was modified.

    Args:
        endpoint (str): url to a remote endpoint
        ehash (str): hash of the endpoint
        query (dict | None): query params of the requested url. Defaults to None.

    Returns:
        bool: `True` if modified.
    """

    lock = lock2
    # None if not found.
    modified: bool | None = None
    url: str = endpoint if not query else endpoint + "?" + urlencode(query=query)

    if lock.locked():
        async with lock:  # pragma: no cover
            pass

    with SQLSession(db_engine) as session:
        # Check for freshness.
        # NOTE: takes 600, 100, 48 ms
        remote_endpoint_data = session.get(TRequestedURL, ehash, with_for_update=True)
        print("\nRemote endpoint data: ", remote_endpoint_data, "\n")
        if remote_endpoint_data:
            response = await request_headers(
                endpoint, query=query, headers={"if-none-match": remote_endpoint_data.etag}
            )
            print("response code: ", response.status_code)
            if response.status_code == status_code.NOT_MODIFIED:
                modified = False
                remote_endpoint_data.requested = datetime.now()
                session.add(remote_endpoint_data)
                session.commit()
            else:
                modified = True
                remote_endpoint_data.etag = response.headers["etag"]
                remote_endpoint_data.requested = datetime.now()
                session.add(remote_endpoint_data)
                session.commit()
        else:
            async with lock:
                response = await request_headers(endpoint, query=query)
                if response.is_success:
                    modified = True
                    session.add(
                        TRequestedURL(
                            id=ehash,
                            url=url,
                            requested=datetime.now(),
                            etag=response.headers["etag"],
                        )
                    )
                    session.commit()
                else:  # pragma: no cover
                    raise ValueError(
                        f"""Remote server returned an unexpected response.\n
                        Dump:\n {ujson.dumps(response, indent=2, escape_forward_slashes=False)}"""
                    )

    return modified


async def is_stale(endpoint: str, ehash: str, query: dict | None = None) -> bool:
    """Check cache for staleness.

    Args:
        endpoint (str): Remote-API endpoint url.
        ehash (str): hash of a remote endpoint
        query (dict | None): query params of the requested url. Defaults to None.


    Returns:
        bool | None: `True` if stale and `None` if cache not found.
    """

    stale: bool | None = None

    with SQLSession(db_engine) as session:
        remote_endpoint_data = session.get(TRequestedURL, ehash)
        if remote_endpoint_data:
            stale = remote_endpoint_data.requested + timedelta(seconds=CACHE_TTL["11days"]) <= datetime.now()

    # Make requests to remote server. Only if cache is considered stale.
    if stale is True or stale is None:
        source_modified = await is_source_modified(endpoint, ehash, query)
        print("Modified: ", source_modified)
        stale = source_modified

    return stale


async def get_local_data(endpoint_requesting_data: str, remote_url_data: DataForRequest) -> ResponseData:
    """Get data for an endpoint.

    Args:
        endpoint_requesting_data (str): Name of the endpoint that's requesting data. Can be any.
        remote_url_data (DataForRequest): Data that will be used to build a request to remote API

    Raises:
        NameError: If `create_` function is not found.

    Returns:
        ResponseData: Generated response.
    """

    # Pagination should also be used to generate endpoint hash. otherwise it will be te same.
    print(remote_url_data.model_dump_json)
    endpoint_hash: str = generate_hash(endpoint_requesting_data, 16, remote_url_data.query)
    function_name: str = "create_" + endpoint_requesting_data.replace("-", "_")
    no_cache: bool = (
        remote_url_data.headers is not None
        and "cache-control" in remote_url_data.headers
        and remote_url_data.headers["cache-control"] == "no-cache"
    )
    stale = await is_stale(remote_url_data.url, remote_url_data.hash_value, remote_url_data.query)
    print("no-cache: ", no_cache)
    print("is stale: ", stale)
    lock = lock1

    if lock.locked():
        async with lock:  # pragma: no cover
            pass

    with SQLSession(db_engine) as session:
        # Check for key
        if no_cache or stale:
            item_content = session.exec(
                select(TContent)
                .where(TContent.id == endpoint_hash)
                .with_for_update()
                .options(selectinload(TContent.header))
            ).one_or_none()
        else:
            item_content = session.get(TContent, endpoint_hash)
            if item_content:
                # Prepare output
                content = b64d(item_content.content)
                return ResponseData(
                    from_cache=True,
                    headers={"etag": item_content.header.etag},
                    body=content,
                )

        async with lock:
            # Create data
            if function_name in globals():
                function_obj = globals()[function_name]
                created_output: CreatedOutput = await function_obj(remote_url_data.url, remote_url_data.query)
            else:
                raise RuntimeError(f"Function name `{function_name}` is not defined.")  # pragma: no cover

            # Write created data
            if (no_cache and item_content) or (stale and item_content):
                item_content.content = b64e(created_output.content)
                item_content.updated = datetime.now()
                item_content.header.etag = created_output.etag
                item_content.source = str(created_output.source)
                add_item = item_content
            else:
                # You could be trying to clear cache, and delete rows from TContent and not from THeaders.
                # By doing this the db integrity is compromised. So now we're trying to avoid integrity errors.
                theaders_data = session.get(THeaders, endpoint_hash)
                if not theaders_data:
                    add_item = TContent(
                        id=endpoint_hash,
                        content=b64e(created_output.content),
                        created=datetime.now(),
                        reference_point=remote_url_data.hash_value,
                        header=THeaders(
                            id=endpoint_hash,
                            etag=created_output.etag,
                        ),
                        source=str(created_output.source),
                    )
                else:
                    add_item = TContent(
                        id=endpoint_hash,
                        content=b64e(created_output.content),
                        created=datetime.now(),
                        reference_point=remote_url_data.hash_value,
                        source=str(created_output.source),
                    )
            session.add(add_item)
            session.commit()

            return ResponseData(
                from_cache=False,
                headers={"etag": created_output.etag},
                body=created_output.content,
            )
