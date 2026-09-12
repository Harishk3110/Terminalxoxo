"""Trusted in-memory model writes; no artifact loading surface is exposed."""

from typing import BinaryIO

def dump(
    value: object, filename: BinaryIO, compress: int = 0, protocol: int | None = None
) -> None: ...
