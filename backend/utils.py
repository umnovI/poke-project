"""Common used functions.
Including usage by `schemas.py`.

Better if they are not `async`. For more convenient usage in schemas.
"""
import base64
import hashlib
import math


def generate_hash(data: str, length: int, query: dict | None = None) -> str:
    """Generate hash of a string using `blake2b`

    Args:
        data (str): endpoint name without leading or trailing slashes.
        length (int): Length of the hash output
        query (dict | None, optional): GET-query. Defaults to None.

    Returns:
        str: Hash-string.
    """

    if query:
        data = data + str(query)
    return hashlib.blake2b(data.encode("UTF-8"), digest_size=length).hexdigest()


def b64e(data: str) -> bytes:
    """Encode string to a base64."""

    return base64.b64encode(data.encode("UTF-8"))


def b64d(data: bytes) -> str:
    """Decode string from a base64."""

    return base64.b64decode(data).decode("UTF-8")


class Paginator:
    """This class handles pagination for lists."""

    def __init__(self, items: list, limit: int | None = None, offset: int | None = None) -> None:
        """Slice list based on pagination params.

        Args:
            items (list): list of items
            limit (int | None, optional): Limit. Defaults to None.
            offset (int | None, optional): Offset. Defaults to None.
        """

        self.__items = items
        self.__count: int = len(items)
        self.__limit: int | None = limit
        self.__offset: int | None = offset
        self.__pages: int = 1
        self.__cur_page: int = 1

    def _calc_pages(self) -> int:
        """Get number of pages"""

        if self.__limit and self.__count > self.__limit:
            self.__pages = math.ceil(self.__count / self.__limit)
            return self.__pages
        return self.__pages

    @property
    def count(self) -> int:
        """Count number of items in list"""

        return self.__count

    def paginate(self) -> list:
        """Return sliced list based on offset and limit"""

        pages = self._calc_pages()
        if self.__offset and self.__limit:
            self.__cur_page = math.ceil(self.__offset / self.__limit) + 1
            print("Current page: ", self.__cur_page, "of ", pages)
            return self.__items[self.__offset : self.__limit + self.__offset]
        if self.__limit:
            print("Current page: ", self.__cur_page, "of ", pages)
            return self.__items[: self.__limit]
        return self.__items

    @property
    def has_next(self) -> bool:
        """Has next page?"""

        if self.__pages <= self.__cur_page:
            return False
        return True

    @property
    def next(self) -> dict[str, int] | None:
        """Generate dict with params for the next page

        Returns:
            dict[str, int] | None: Return `None` if unable to generate or doesn't have next.
        """
        if not self.has_next:
            return None

        if not self.__offset and self.__limit:
            offset = self.__limit
        elif self.__offset and self.__limit:
            offset = self.__offset + self.__limit
        else:
            return None

        return {"offset": offset, "limit": self.__limit}
