import asyncio

import allure
import pytest


@pytest.fixture(scope="session")
@allure.title("Selecting asyncio library")
def anyio_backend():
    return "asyncio"


@pytest.fixture(scope="session")
@allure.title("Asyncio event loop.")
def event_loop():
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
    yield loop
    loop.close()
