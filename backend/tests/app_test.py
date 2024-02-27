# pylint: disable=redefined-outer-name
import asyncio
import base64
import os
import random
from datetime import datetime
from pathlib import Path
from typing import Any, Literal
from urllib import parse

import pytest
from hishel._utils import generate_key
from httpcore import Request
from httpx import ASGITransport, AsyncClient, Response
from pytest_httpx import HTTPXMock
from sqlalchemy import Engine
from sqlmodel import Session as SQLSession
from sqlmodel import SQLModel, create_engine

import backend.api
import backend.localdata
from backend.app import EndpointName, app
from backend.db_config import TContent, THeaders, TPartialContent, TRequestedURL
from backend.secrets import TEST_DATABASE_URL
from backend.shared_config import CACHE_TTL, HOST
from backend.utils import generate_hash

pytestmark = pytest.mark.anyio


@pytest.fixture(scope="session")
def monkeysession():
    with pytest.MonkeyPatch.context() as mp:
        yield mp


@pytest.fixture(scope="session")
def db_engine():
    engine = create_engine(TEST_DATABASE_URL)
    SQLModel.metadata.create_all(engine)
    yield engine
    SQLModel.metadata.drop_all(engine)
    engine.dispose()


@pytest.fixture(scope="function")
def db_session(db_engine: Engine):
    with SQLSession(db_engine) as session:
        yield session


@pytest.fixture(scope="function", autouse=True)
def patched_db_session(db_session: SQLSession, monkeypatch: pytest.MonkeyPatch):
    def get_db_session_override(*args):  # pylint: disable=W0613
        return db_session

    # Override db session with our test session.
    monkeypatch.setattr(backend.localdata, "SQLSession", get_db_session_override)
    monkeypatch.setattr(backend.api, "SQLSession", get_db_session_override)


@pytest.fixture(scope="session")
async def client():
    http_client = AsyncClient(
        transport=ASGITransport(app=app),  # type: ignore (Incompatible types?)
        base_url="http://test",
        headers={"user-agent": "test-script/app-tests"},
    )
    yield http_client
    await http_client.aclose()


@pytest.fixture()
def cache_ttl_override(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setitem(CACHE_TTL, "11days", 0)


# Global testing


@pytest.mark.dependency()
async def test_cache_ttl_override(cache_ttl_override):  # pylint: disable=W0613
    assert CACHE_TTL["11days"] == 0


# Test Database


@pytest.mark.dependency()
async def test_database_session(db_session: SQLSession):
    db_session.add_all(
        (
            TContent(
                id="test_data",
                content=base64.b64encode("test".encode("utf-8")),
                created=datetime.now(),
                reference_point="reference",
                header=THeaders(
                    id="test_data",
                    etag="test_etag",
                ),
                source=str("pytest_mock"),
            ),
            TRequestedURL(
                id="reference",
                url="url",
                requested=datetime.now(),
                etag="response_etag",
            ),
        )
    )
    db_session.commit()
    data = db_session.get(TContent, "test_data")
    assert data is not None
    assert data.id == "test_data"
    assert data.content == base64.b64encode("test".encode("utf-8"))


@pytest.mark.dependency(depends=["test_database_session"])
async def test_db_data_accessability_from_another_test(db_session: SQLSession):
    data = db_session.get(TContent, "test_data")
    assert data is not None
    assert data.id == "test_data"
    assert data.content == base64.b64encode("test".encode("utf-8"))


# Endpoints Testing Start


async def test_server_422(client: AsyncClient):
    response = await client.get("/api/unprocessable/")
    assert response.status_code == 422


async def test_server_404(client: AsyncClient, httpx_mock: HTTPXMock):
    httpx_mock.add_response(status_code=404)

    # Test named endpoint 404 response from remote server
    async def job(item: EndpointName):
        response = await client.get(f"/api/{item.value}/not-found/")
        assert response.status_code == 404
        assert (
            response.text
            == '{"detail":'
            + f'"Error {response.status_code} occurred while requesting {HOST.data}/{item.value}/not-found/"'
            + "}"
        )

    tasks = [job(item) for item in EndpointName]
    await asyncio.gather(*tasks)

    # Test media endpoint 404
    response = await client.get("/api/media/?f=L1Bva2VBUEkvdGVzdC90ZXN0LzQwNC5qcGc=")
    assert response.status_code == 404
    assert response.text == '{"detail":' + f'"Error {response.status_code} occurred while requesting media file."' + "}"


async def test_server_500(client: AsyncClient, httpx_mock: HTTPXMock):
    httpx_mock.add_response(status_code=500)

    async def job(item: EndpointName):
        response = await client.get(f"/api/{item.value}/i-am-500/")
        assert response.status_code == 500
        assert (
            response.text
            == '{"detail":'
            + f'"Error {response.status_code} occurred while requesting {HOST.data}/{item.value}/i-am-500/"'
            + "}"
        )

    tasks = [job(item) for item in EndpointName]
    await asyncio.gather(*tasks)


@pytest.mark.dependency()
async def test_endpointname(client: AsyncClient):
    tasks = [client.get("/api/" + endpoint.value + "/") for endpoint in EndpointName]
    results = await asyncio.gather(*tasks)
    for response in results:
        assert response.status_code == 200


@pytest.mark.dependency()
@pytest.mark.dependency(depends=["test_endpointname"])
async def test_pagination(client: AsyncClient):
    response = await client.get("/api/pokemon/?offset=20&limit=20")
    assert response.status_code == 200

    # Select data out of range
    response = await client.get("/api/pokemon/?offset=4000&limit=20")
    assert response.status_code == 404


@pytest.mark.dependency(depends=["test_endpointname"])
async def test_endpoint_name_database_cache(client: AsyncClient, db_session: SQLSession):
    async def job(endpoint: EndpointName) -> None:
        lock = asyncio.Lock()
        endpoint_hash: str = generate_hash("/" + endpoint.value + "/", 16)
        db_cache = db_session.get(TPartialContent, endpoint_hash)
        assert db_cache is not None
        old_date = db_cache.created
        await asyncio.sleep(1)
        # I can't mock response.extensions["from_cache"]. So the only way was is to delete cache.
        # Now we need to generate cache key.
        cache_key = generate_key(
            Request(
                "GET",
                HOST.data + "/" + endpoint.value + "/",
            )
        )
        async with lock:
            if Path("./.cache/hishel/" + cache_key).is_file():
                os.unlink("./.cache/hishel/" + cache_key)
        response = await client.get("/api/" + endpoint.value + "/")
        assert response.status_code == 200
        db_cache = db_session.get(TPartialContent, endpoint_hash)
        assert db_cache is not None
        assert db_cache.updated is not None
        new_date = db_cache.updated
        assert old_date != new_date

    tasks = [job(endpoint) for endpoint in EndpointName]
    await asyncio.gather(*tasks)


@pytest.mark.dependency(depends=["test_endpointname"])
async def test_browser_caching(client: AsyncClient):
    url: list[str] = []
    for endpoint in EndpointName:
        url.append("/api/" + endpoint.value + "/")
    request_200 = [client.get(cur_url) for cur_url in url]
    result_200 = await asyncio.gather(*request_200)

    request_304 = []
    for i, response in enumerate(result_200):
        assert response.status_code == 200
        request_304.append(asyncio.create_task(client.get(url[i], headers={"If-None-Match": response.headers["etag"]})))

    result_304: list[Response] = await asyncio.gather(*request_304)
    for response in result_304:
        assert response.status_code == 304


# Individual item testing


@pytest.mark.dependency(depends=["test_pagination"])
@pytest.mark.parametrize(
    "name, url, get_from",
    [
        ("caterpie", "/api/pokemon/10/", "/api/pokemon/"),
        ("raticate", "/api/pokemon/20/", "/api/pokemon/"),
        ("charizard", "/api/pokemon/6/", "/api/pokemon/"),
        ("metapod", "/api/pokemon/11/", "/api/pokemon/"),
        ("spearow", "/api/pokemon/21/", "/api/pokemon/?offset=20&limit=20"),
        ("arbok", "/api/pokemon/24/", "/api/pokemon/?offset=20&limit=20"),
        ("nidorino", "/api/pokemon/33/", "/api/pokemon/?offset=20&limit=20"),
        ("ninetales", "/api/pokemon/38/", "/api/pokemon/?offset=20&limit=20"),
        ("wigglytuff", "/api/pokemon/40/", "/api/pokemon/?offset=20&limit=20"),
        ("zubat", "/api/pokemon/41/", "/api/pokemon/?offset=40&limit=20"),
        ("poliwag", "/api/pokemon/60/", "/api/pokemon/?offset=40&limit=20"),
    ],
)
async def test_pokemon_data_correctness(client: AsyncClient, name, url, get_from):
    response = await client.get(get_from)
    assert response.status_code == 200
    list_of_names = []
    list_of_urls = []
    for result in response.json()["results"]:
        list_of_names.append(result["name"])
        list_of_urls.append(result["url"])

    assert name in list_of_names
    assert url in list_of_urls


@pytest.mark.dependency()
async def test_berry(client: AsyncClient):
    response = await client.get("/api/berry/")
    assert response.status_code == 200
    assert "results" in response.json()
    assert "count" in response.json()


@pytest.mark.dependency(depends=["test_berry"])
@pytest.mark.parametrize(
    "id_name, expected, key",
    [
        (1, "cheri", "id"),
        (2, "chesto", "id"),
        ("cheri", 1, "name"),
        ("chesto", 2, "name"),
    ],
)
async def test_berry_id_name(
    id_name: Literal[1, 2, "cheri", "chesto"],
    expected: Literal["cheri", "chesto", 1, 2],
    key: Literal["id", "name"],
    client: AsyncClient,
):
    response = await client.get(f"/api/berry/{id_name}/")
    assert response.status_code == 200
    assert response.json()[key] == id_name
    match key:
        case "id":
            assert response.json()["name"] == expected
        case "name":
            assert response.json()["id"] == expected


@pytest.mark.dependency(depends=["test_berry"])
async def test_berry_item(client: AsyncClient):
    berry_response = await client.get("/api/berry/")

    # converting list -> list bc of the pylint unsubscriptable-object error
    items: list[dict[str, str]] = list(random.sample(berry_response.json()["results"], 5))
    for item in items:
        item_response = await client.get(item["url"])
        assert item_response.status_code == 200
        assert "firmness" in item_response.json()
        assert "flavors" in item_response.json()


@pytest.mark.parametrize(
    "id_name",
    [
        (1),
        (2),
        ("bulbasaur"),
        ("ivysaur"),
    ],
)
async def test_pokemon_id_name_encounters(client: AsyncClient, id_name: Literal[1, 2, "bulbasaur", "ivysaur"]):
    response = await client.get(f"/api/pokemon/{id_name}/encounters/")
    assert response.status_code == 200


@pytest.mark.parametrize("id_", [(1), (2), (3), (4)])
async def test_media_fetch(client: AsyncClient, id_: int):
    response = await client.get(f"/api/pokemon/{id_}/")
    assert response.status_code == 200
    r_img1 = await client.get(response.json()["sprites"]["back_default"])
    assert r_img1.status_code == 200
    assert r_img1.headers["content-type"] == "image/png"
    r_img2 = await client.get(response.json()["sprites"]["back_shiny"])
    assert r_img2.status_code == 200
    assert r_img2.headers["content-type"] == "image/png"
    r_img3 = await client.get(response.json()["sprites"]["front_shiny"])
    assert r_img3.status_code == 200
    assert r_img3.headers["content-type"] == "image/png"
    r_img4 = await client.get(response.json()["sprites"]["other"]["dream_world"]["front_default"])
    assert r_img4.status_code == 200
    assert r_img4.headers["content-type"] == "image/svg+xml"


@pytest.mark.dependency()
async def test_get_pokemon_detailed_200(client: AsyncClient):
    response = await client.get("/api/pokemon-detailed/")
    assert response.status_code == 200


@pytest.mark.dependency(depends=["test_get_pokemon_detailed_200"])
async def test_simultaneous_transaction(client: AsyncClient):
    # Sqlalchemy hates concurrency. Most of the errors caused by it.
    # https://docs.sqlalchemy.org/en/14/orm/extensions/asyncio.html

    async with asyncio.TaskGroup() as tg:
        tasks = [
            tg.create_task(client.get("/api/pokemon-detailed/", headers={"cache-control": "no-cache"}))
            for _ in range(3)
        ]
        tasks.append(tg.create_task(client.get("/api/pokemon-detailed/")))
        tasks.append(tg.create_task(client.get("/api/pokemon-detailed/")))

    assert tasks[0].result().status_code == 200
    assert tasks[1].result().status_code == 503
    assert tasks[2].result().status_code == 503
    # Integrity error:
    assert tasks[3].result().status_code == 200
    assert tasks[4].result().status_code == 200


@pytest.fixture
async def pokemon_detailed(client: AsyncClient):
    response = await client.get("/api/pokemon-detailed/")
    return response


@pytest.mark.dependency(depends=["test_get_pokemon_detailed_200"])
async def test_get_pokemon_detailed_content(pokemon_detailed: Response):
    data = pokemon_detailed.json()

    assert "results" in data
    for result in data["results"]:
        assert "sprites" in result
        assert len(result["sprites"]) != 0


@pytest.mark.dependency(depends=["test_get_pokemon_detailed_200"])
async def test_get_pokemon_detailed_304(client: AsyncClient, pokemon_detailed: Response):
    response = pokemon_detailed
    resp_304 = await client.get("/api/pokemon-detailed/", headers={"If-None-Match": response.headers["etag"]})
    assert resp_304.status_code == 304


@pytest.mark.dependency(depends=["test_get_pokemon_detailed_200"])
async def test_get_pokemon_detailed_pagination(client: AsyncClient, pokemon_detailed: Response):
    data = pokemon_detailed.json()
    counter: int = 0

    while counter < 5 and data["next"] is not None:
        counter += 1
        resp_next = await client.get(data["next"])
        data["next"] = resp_next.json()["next"]
        assert resp_next.status_code == 200
        assert "results" in resp_next.json()
        for result in resp_next.json()["results"]:
            assert "sprites" in result
            assert len(result["sprites"]) != 0


@pytest.mark.dependency(depends=["test_get_pokemon_detailed_200"])
async def test_pokemon_detailed_update_data(client: AsyncClient):
    response = await client.get("/api/pokemon-detailed/", headers={"cache-control": "no-cache"})
    assert response.status_code == 200
    data = response.json()
    counter: int = 0

    while counter < 5 and data["next"] is not None:
        counter += 1
        print("counter:", counter)
        resp_next = await client.get(data["next"], headers={"cache-control": "no-cache"})
        data["next"] = resp_next.json()["next"]
        assert resp_next.status_code == 200
        assert "results" in resp_next.json()
        for result in resp_next.json()["results"]:
            assert "sprites" in result
            assert len(result["sprites"]) != 0


@pytest.mark.dependency(depends=["test_cache_ttl_override", "test_get_pokemon_detailed_200"])
async def test_pokemon_detailed_data_fresh(
    client: AsyncClient, cache_ttl_override, db_session: SQLSession, httpx_mock: HTTPXMock
):  # pylint: disable=W0613
    httpx_mock.add_response(status_code=304, method="HEAD", headers={"etag": "this_is_old_etag"})
    await asyncio.sleep(1)
    endpoint_hash: str = generate_hash("pokemon-detailed", 16)

    old_db_content = db_session.get(TContent, endpoint_hash)
    assert old_db_content is not None
    old_db_requested = db_session.get(TRequestedURL, old_db_content.reference_point)
    assert old_db_requested is not None

    response = await client.get("/api/pokemon-detailed/")
    assert response.status_code == 200

    db_content = db_session.get(TContent, endpoint_hash)
    assert db_content is not None
    db_requested = db_session.get(TRequestedURL, db_content.reference_point)
    assert db_requested is not None
    assert db_requested.requested != old_db_requested.requested
    if db_content.updated is not None:
        assert db_content.updated != db_requested.requested
    else:
        assert db_content.created != db_requested.requested


@pytest.mark.dependency(depends=["test_cache_ttl_override", "test_get_pokemon_detailed_200"])
async def test_pokemon_detailed_data_stale(
    client: AsyncClient, cache_ttl_override, db_session: SQLSession, httpx_mock: HTTPXMock
):  # pylint: disable=W0613
    httpx_mock.add_response(status_code=200, method="HEAD", headers={"etag": "this_is_new_etag"})
    await asyncio.sleep(1)
    endpoint_hash: str = generate_hash("pokemon-detailed", 16)
    old_db_content = db_session.get(TContent, endpoint_hash)
    assert old_db_content is not None
    old_db_requested = db_session.get(TRequestedURL, old_db_content.reference_point)
    assert old_db_requested is not None

    response = await client.get("/api/pokemon-detailed/")
    assert response.status_code == 200
    db_content = db_session.get(TContent, endpoint_hash)
    assert db_content is not None
    assert db_content.updated is not None
    assert db_content.updated != old_db_content.updated
    db_requested = db_session.get(TRequestedURL, db_content.reference_point)
    assert db_requested is not None
    assert db_requested.requested != old_db_requested.requested
    assert db_requested.etag == "this_is_new_etag"


async def test_keeping_db_integrity_during_get_local_data(client: AsyncClient, db_session: SQLSession):
    # Tests partial cache removal by hand
    response = await client.get("/api/pokemon-detailed/")
    assert response.status_code == 200
    endpoint_id = generate_hash("pokemon-detailed", 16)
    db_data = db_session.get(TContent, endpoint_id, with_for_update=True)
    assert db_data is not None
    db_session.delete(db_data)
    db_session.commit()
    db_data = db_session.get(TContent, endpoint_id, with_for_update=True)
    assert db_data is None
    response = await client.get("/api/pokemon-detailed/")
    assert response.status_code == 200
    db_data = db_session.get(TContent, endpoint_id, with_for_update=True)
    assert db_data is not None


# Response time test


async def test_endpointname_response_time(client: AsyncClient):
    for endpoint in EndpointName:
        response = await client.get("/api/" + endpoint.value + "/")
        assert response.status_code == 200
        print(response.elapsed.total_seconds())
        # Second request should be taken from cache and as result much faster.
        assert response.elapsed.total_seconds() < 1


async def test_pokemon_detailed_response_time(client: AsyncClient):
    response = await client.get("/api/pokemon-detailed/")
    assert response.status_code == 200
    print(response.elapsed.total_seconds())
    # Second request should be taken from cache and as result much faster.
    assert response.elapsed.total_seconds() < 1


async def test_get_local_media_200(client: AsyncClient):
    response = await client.get("/api/media/?l=test.jpg")
    assert response.status_code == 200


async def test_get_local_media_404(client: AsyncClient):
    response = await client.get("/api/media/?l=notfound.jpg")
    assert response.status_code == 404


async def test_media_400(client: AsyncClient):
    response = await client.get("/api/media/?a")
    assert response.status_code == 400


@pytest.mark.parametrize(
    "subject, search, expected",
    [
        (
            "pokemon",
            "pika",
            {
                "count": 17,
                "found": [
                    "pikachu",
                    "pikachu-rock-star",
                    "pikachu-belle",
                    "pikachu-pop-star",
                    "pikachu-phd",
                    "pikachu-libre",
                    "pikachu-cosplay",
                    "pikachu-original-cap",
                    "pikachu-hoenn-cap",
                    "pikachu-sinnoh-cap",
                    "pikachu-unova-cap",
                    "pikachu-kalos-cap",
                    "pikachu-alola-cap",
                    "pikachu-partner-cap",
                    "pikachu-starter",
                    "pikachu-world-cap",
                    "pikachu-gmax",
                ],
                "next": None,
            },
        ),
        (
            "pokemon",
            "null",
            {
                "count": 1,
                "found": ["type-null"],
                "next": None,
            },
        ),
        (
            "pokemon",
            "cat",
            {
                "count": 7,
                "found": [
                    "caterpie",
                    "raticate",
                    "delcatty",
                    "scatterbug",
                    "torracat",
                    "raticate-alola",
                    "raticate-totem-alola",
                ],
                "next": None,
            },
        ),
        (
            "ability",
            "battle ar",
            {
                "count": 1,
                "found": ["battle-armor"],
                "next": None,
            },
        ),
        (
            "ability",
            "sta",
            {
                "count": 9,
                "found": [
                    "static",
                    "stall",
                    "slow-start",
                    "victory-star",
                    "stance-change",
                    "stamina",
                    "stakeout",
                    "stalwart",
                    "costar",
                ],
                "next": None,
            },
        ),
    ],
)
async def test_search_query(client: AsyncClient, subject: str, search: str, expected: dict):
    response = await client.get(
        f"/api/search/{subject}/?q={parse.quote_plus(search)}", headers={"Cache-Control": "no-cache"}
    )
    assert response.status_code == 200
    data: dict[str, Any] = response.json()
    assert data["count"] == expected["count"]
    assert data["next"] == expected["next"]
    assert [result["name"] for result in data["results"]] == expected["found"]


@pytest.mark.parametrize(
    "subject, search, offset, limit, expected",
    [
        (
            "berry",
            "a",
            None,
            2,
            {
                "count": 30,
                "found": [
                    "pecha",
                    "rawst",
                ],
                "next": {"offset": "2", "limit": "2", "q": "a"},
            },
        ),
        (
            "berry",
            "la",
            2,
            2,
            {
                "count": 3,
                "found": ["lansat"],
                "next": None,
            },
        ),
    ],
)
async def test_search_query_with_pagination(
    client: AsyncClient, subject: str, search: str, offset: str | None, limit: str | None, expected: dict
):
    send_query: dict[str, str] = {"q": parse.quote_plus(search)}
    if offset:
        send_query["offset"] = offset
    if limit:
        send_query["limit"] = limit

    response = await client.get(
        f"/api/search/{subject}/?{parse.urlencode(query=send_query)}",
        headers={"Cache-Control": "no-cache"},
    )
    assert response.status_code == 200
    data: dict[str, Any] = response.json()
    assert data["count"] == expected["count"]
    if expected["next"]:
        assert dict(parse.parse_qsl(parse.urlsplit(data["next"]).query)) == expected["next"]
    else:
        assert data["next"] == expected["next"]
    assert [result["name"] for result in data["results"]] == expected["found"]
