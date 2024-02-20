from asyncio import Task, TaskGroup

from backend.dependencies import make_request
from backend.schemas import ResponseData


async def build_found_list(subject: str, names: list[tuple]) -> dict:
    tasks: list[Task[ResponseData]] = []
    results: list = []

    try:
        async with TaskGroup() as tg:
            for pokemon in names:
                tasks.append(tg.create_task(make_request(f"/{subject}/{pokemon[0]}")))
    except ExceptionGroup as e:  # pragma: no cover
        raise e

    for result in tasks:
        data = result.result()
        results.append(
            {
                "name": data.body["name"],
                "sprites": data.body["sprites"],
            }
        )

    output: dict = {
        "count": len(names),
        "results": results,
    }
    return output
