"""Constants and settings."""

# Define the client
import hishel
from httpx import Limits

from backend.schemas import Hosts

HOST = Hosts(
    data="https://pokeapi.co/api/v2",
    media="https://raw.githubusercontent.com",
)

CACHE_TTL = {"11days": 950400}
HISHEL_STORAGE = hishel.AsyncFileStorage()
HISHEL_CONTROLLER = hishel.Controller(allow_stale=True)
HISHEL_CLIENT = hishel.AsyncCacheClient(
    storage=HISHEL_STORAGE,
    controller=HISHEL_CONTROLLER,
    limits=Limits(max_connections=50),
)
