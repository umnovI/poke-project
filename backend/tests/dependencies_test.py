import pytest
from fastapi import HTTPException
from pytest_httpx import HTTPXMock

from backend.dependencies import request_headers

pytestmark = pytest.mark.anyio


async def test_request_headers(httpx_mock: HTTPXMock):
    httpx_mock.add_response(status_code=404)

    with pytest.raises(HTTPException) as err:
        await request_headers("/test/")
    assert err.type == HTTPException
