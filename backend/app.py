from asyncio import Lock
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Annotated, Any
from urllib.parse import quote_plus, urlencode

import ujson
from api_analytics.fastapi import Analytics
from fastapi import BackgroundTasks, FastAPI, Header, HTTPException, Query, Response
from fastapi.responses import FileResponse
from pydantic import Base64UrlStr, Json
from thefuzz import process
from werkzeug.utils import secure_filename

from backend.common import generate_hash
from backend.db_config import close_db_connections, create_tables
from backend.dependencies import PaginationQuery, Paginator, etag_compare, make_media_request, make_request
from backend.endpoints import EndpointName
from backend.filters import build_found_list
from backend.localdata import get_local_data
from backend.schemas import DataForRequest
from backend.secrets import ANALYTICS_API
from backend.shared_config import HISHEL_CLIENT


@asynccontextmanager
async def lifespan(app: FastAPI):  # pragma: no cover, pylint: disable=redefined-outer-name, unused-argument
    # Startup code
    await create_tables()
    yield
    # Exiting code
    # Cleaning up
    await HISHEL_CLIENT.aclose()
    await close_db_connections()


app = FastAPI(
    title="PokeAPI retranslator with caching",
    lifespan=lifespan,
)

if ANALYTICS_API is not None:
    print("Setting up Analytics middleware.")
    app.add_middleware(Analytics, api_key=ANALYTICS_API)  # Add middleware
else:  # pragma: no cover
    print("Analytics key was not found. Analytics middleware is not set.")

lock = Lock()


@app.get("/favicon.ico", include_in_schema=False)
async def favicon():
    # Favicon is requested only by browsers.
    return FileResponse("backend/static/favicon.ico")  # pragma: no cover


@app.get(
    "/api/media/",
    responses={
        200: {
            "content": {
                "image/png": {},
                "image/svg+xml": {},
                "image/jpg": {},
            },
            "description": "Return an image.",
        }
    },
    response_model=None,
)
async def get_media_file(
    f: Annotated[
        Base64UrlStr | None,
        Query(max_length=150, pattern=r"^/PokeAPI/.*?/[a-zA-Z|-]+/[0-9]+\.[a-z]{3}$"),
    ] = None,
    l: str | None = None,
    if_none_match: Annotated[str | None, Header()] = None,
    cache_control: Annotated[str | None, Header()] = None,
) -> Response | FileResponse:
    if f:
        media_response = await make_media_request(f)

        if cache_control != "no-cache":
            await etag_compare(if_none_match, media_response.headers)

        return Response(
            media_response.body,
            media_type=media_response.headers["content-type"],
            headers={
                "etag": media_response.headers["etag"],
            },
        )
    if l:
        sfilename = secure_filename(l)
        if sfilename:
            filepath = Path(f"./backend/static/{sfilename}")
            if filepath.is_file():
                statresult = filepath.stat()
                etag = generate_hash(str(statresult.st_size) + "-" + str(statresult.st_mtime), 10)
                if cache_control != "no-cache":
                    await etag_compare(if_none_match, {"etag": etag})
                return FileResponse(filepath, headers={"etag": etag})

        raise HTTPException(404)

    raise HTTPException(400)


@app.get("/api/pokemon-detailed/")
async def get_pokemon_detailed(
    pagination: PaginationQuery,
    response: Response,
    if_none_match: Annotated[str | None, Header()] = None,
    cache_control: Annotated[str | None, Header()] = None,
) -> Json:
    async def job():
        return await get_local_data(
            "pokemon-detailed",
            DataForRequest(
                url="/pokemon/",
                query=pagination,
                headers={
                    "cache-control": cache_control,
                }
                if cache_control is not None
                else None,
            ),
        )

    if cache_control == "no-cache":
        if lock.locked():
            raise HTTPException(503, "Busy. Please try again later.")

        async with lock:
            res = await job()
    else:
        res = await job()

    if res.headers is not None:
        if cache_control != "no-cache":
            await etag_compare(if_none_match, res.headers)

        for header in res.headers:
            response.headers[header] = res.headers[header]

    return res.body


@app.get("/api/search/{subject}/")
async def get_item_by_search(
    subject: EndpointName,
    pagination: PaginationQuery,
    q: str,
    cache_control: Annotated[str | None, Header()] = None,
):
    query: str = quote_plus(q)
    data = await get_local_data(
        "search-list",
        DataForRequest(
            url=f"/{subject.value}/",
            headers={"cache-control": cache_control} if cache_control is not None else None,
        ),
    )
    parsed_data: dict[str, Any] = ujson.loads(data.body)
    names = [result["name"] for result in parsed_data["results"]]
    # Package doesn't support type hints
    # Follow this PR to know if this has changed https://github.com/seatgeek/thefuzz/pull/71
    found: list[tuple] = process.extractBests(query, names, score_cutoff=80, limit=30)  # type: ignore
    # We need to get icons on them. We can't get this during prev step bc
    # we'd have to go over 1000+ items instead of `limit`
    paginator = Paginator(found, pagination["limit"], pagination["offset"])
    result = await build_found_list(subject.value, paginator.paginate())
    result["count"] = paginator.get_count()
    next_query = paginator.generate_next()
    if next_query and paginator.has_next():
        result["next"] = f"/api/search/{subject.value}/?{urlencode(query=next_query)}&q={query}"
    else:
        result["next"] = None

    return result


@app.get("/api/filter/{subject}/")
async def get_item_by_filter(subject: EndpointName):
    return {"subject": subject}


@app.get("/api/pokemon/{id_name}/encounters/")
async def get_pokemon_encounters(
    id_name: int | str,
    response: Response,
    background_tasks: BackgroundTasks,
    if_none_match: Annotated[str | None, Header()] = None,
    cache_control: Annotated[str | None, Header()] = None,
) -> list[dict]:
    remote_api = await make_request(f"/pokemon/{id_name}/encounters/", background_tasks=background_tasks)

    if remote_api.headers is not None:
        if cache_control != "no-cache":
            await etag_compare(if_none_match, remote_api.headers)
        for header in remote_api.headers:
            response.headers[header] = remote_api.headers[header]

    return remote_api.body


@app.get("/api/{endpoint}/")
async def get_group(
    response: Response,
    endpoint: EndpointName,
    pagination: PaginationQuery,
    background_tasks: BackgroundTasks,
    if_none_match: Annotated[str | None, Header()] = None,
    cache_control: Annotated[str | None, Header()] = None,
) -> dict:
    remote_api = await make_request(f"/{endpoint.value}/", pagination, background_tasks=background_tasks)

    if remote_api.headers is not None:
        if cache_control != "no-cache":
            await etag_compare(if_none_match, remote_api.headers)
        for header in remote_api.headers:
            response.headers[header] = remote_api.headers[header]

    return remote_api.body


@app.get("/api/{endpoint}/{id_name}/")
async def get_item(
    endpoint: EndpointName,
    id_name: int | str,
    response: Response,
    background_tasks: BackgroundTasks,
    if_none_match: Annotated[str | None, Header()] = None,
    cache_control: Annotated[str | None, Header()] = None,
) -> dict:
    remote_api = await make_request(f"/{endpoint.value}/{id_name}/", background_tasks=background_tasks)

    if remote_api.headers is not None:
        if cache_control != "no-cache":
            await etag_compare(if_none_match, remote_api.headers)
        for header in remote_api.headers:
            response.headers[header] = remote_api.headers[header]

    return remote_api.body
