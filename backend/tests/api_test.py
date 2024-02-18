import pytest

from backend.api import format_links

pytestmark = pytest.mark.anyio


@pytest.mark.parametrize(
    "url, expected",
    [
        ("https://test.co/api/v2/pokemon?offset=20&limit=20", "/api/pokemon?offset=20&limit=20"),
        ("https://test.co/api/v2/pokemon/4/", "/api/pokemon/4/"),
        ("https://test.co/api/v2/ability/65/", "/api/ability/65/"),
        (
            '"https://test-media.co/PokeAPI/sprites/master/sprites/pokemon/versions/generation-vi/x-y/1.png"',
            '"/api/media/?f=L1Bva2VBUEkvc3ByaXRlcy9tYXN0ZXIvc3ByaXRlcy9wb2tlbW9uL3ZlcnNpb25zL2dlbmVyYXRpb24tdmkveC15LzEucG5n"',
        ),
        (
            '"https://test-media.co/PokeAPI/sprites/master/sprites/pokemon/versions/generation-vi/x-y/shiny/1.png"',
            '"/api/media/?f=L1Bva2VBUEkvc3ByaXRlcy9tYXN0ZXIvc3ByaXRlcy9wb2tlbW9uL3ZlcnNpb25zL2dlbmVyYXRpb24tdmkveC15L3NoaW55LzEucG5n"',
        ),
    ],
)
async def test_format_links(url, expected):
    formatted = await format_links(
        url,
        "https://test.co/api/v2",
        "https://test-media.co",
    )
    assert formatted == expected
