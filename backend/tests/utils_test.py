from hmac import compare_digest
from typing import Any

import pytest
from pydantic import BaseModel

from ..utils import Paginator, generate_hash


class NextModel(BaseModel):
    offset: int
    limit: int


class PaginatorExpected(BaseModel):
    count: int
    pages: int
    cur_page: int
    paginate: list[Any]
    has_next: bool
    next_params: NextModel | None


@pytest.mark.parametrize(
    "req1, req2, expected",
    [
        (("test", {}), ("test", {}), True),
        (("test", {}), ("test1", {}), False),
        (("test", {"test1": 1}), ("test", {"test1": 1}), True),
        (("test", {"t": "t"}), ("test1", {"t": "t"}), False),
        (("test", {"t": "t2"}), ("test", {"t": "t"}), False),
    ],
)
def test_generate_hash(
    req1: tuple,
    req2: tuple,
    expected: bool,
):
    hash1 = generate_hash(req1[0], 10, req1[1])
    hash2 = generate_hash(req2[0], 10, req2[1])
    assert compare_digest(hash1, hash2) is expected


dummy_list1 = ["one", "two", "three", "four", "five", "six", "seven", "eight"]
dummy_list_count = len(dummy_list1)


@pytest.mark.parametrize(
    "items,  offset, limit, expected",
    [
        (
            dummy_list1,
            2,
            2,
            PaginatorExpected(
                pages=4,
                cur_page=2,
                count=dummy_list_count,
                paginate=["three", "four"],
                has_next=True,
                next_params=NextModel(offset=4, limit=2),
            ),
        ),
        (
            dummy_list1,
            0,
            2,
            PaginatorExpected(
                pages=4,
                cur_page=1,
                count=dummy_list_count,
                paginate=["one", "two"],
                has_next=True,
                next_params=NextModel(offset=2, limit=2),
            ),
        ),
        (
            dummy_list1,
            6,
            2,
            PaginatorExpected(
                pages=4,
                cur_page=4,
                count=dummy_list_count,
                paginate=["seven", "eight"],
                has_next=False,
                next_params=None,
            ),
        ),
        (
            dummy_list1,
            6,
            3,
            PaginatorExpected(
                pages=3,
                cur_page=3,
                count=dummy_list_count,
                paginate=["seven", "eight"],
                has_next=False,
                next_params=None,
            ),
        ),
        (
            dummy_list1,
            8,
            2,
            PaginatorExpected(
                pages=4,
                cur_page=5,
                count=dummy_list_count,
                paginate=[],
                has_next=False,
                next_params=None,
            ),
        ),
        (
            dummy_list1,
            2,
            0,
            PaginatorExpected(
                pages=1,
                cur_page=1,
                count=dummy_list_count,
                paginate=dummy_list1,
                has_next=False,
                next_params=None,
            ),
        ),
        (
            dummy_list1,
            4,
            4,
            PaginatorExpected(
                pages=2,
                cur_page=2,
                count=dummy_list_count,
                paginate=["five", "six", "seven", "eight"],
                has_next=False,
                next_params=None,
            ),
        ),
        (
            dummy_list1,
            0,
            12,
            PaginatorExpected(
                pages=1,
                cur_page=1,
                count=dummy_list_count,
                paginate=dummy_list1,
                has_next=False,
                next_params=None,
            ),
        ),
        (
            dummy_list1,
            None,
            None,
            PaginatorExpected(
                pages=1,
                cur_page=1,
                count=dummy_list_count,
                paginate=dummy_list1,
                has_next=False,
                next_params=None,
            ),
        ),
        (
            dummy_list1,
            None,
            3,
            PaginatorExpected(
                pages=3,
                cur_page=1,
                count=dummy_list_count,
                paginate=["one", "two", "three"],
                has_next=True,
                next_params=NextModel(offset=3, limit=3),
            ),
        ),
        (
            dummy_list1,
            2,
            None,
            PaginatorExpected(
                pages=1,
                cur_page=1,
                count=dummy_list_count,
                paginate=dummy_list1,
                has_next=False,
                next_params=None,
            ),
        ),
    ],
)
def test_paginator(items: list, limit: int, offset: int, expected: PaginatorExpected):
    paginator = Paginator(items, limit, offset)
    assert paginator.paginate() == expected.paginate
    assert paginator.count == expected.count
    assert paginator._calc_pages() == expected.pages  # pylint: disable=protected-access
    assert getattr(paginator, "_Paginator__cur_page") == expected.cur_page
    assert paginator.has_next == expected.has_next
    if expected.next_params:
        assert paginator.next == expected.next_params.model_dump()
    else:
        assert paginator.next is expected.next_params
