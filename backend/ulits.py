"""Common used functions.
Including usage by `schemas.py`.

Better if they are not `async`. For more convenient usage in schemas.
"""
import base64
import hashlib


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
