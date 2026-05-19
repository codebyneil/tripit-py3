"""Auto-paginating iterator helper for `list_*` endpoints."""

from __future__ import annotations

from collections.abc import Callable, Iterator
from typing import TypeVar

from tripit.models.envelope import Response

T = TypeVar("T")


def paginate(
    fetch_page: Callable[[int], Response],
    pluck: Callable[[Response], list[T]],
) -> Iterator[T]:
    """Yield every item across every page returned by `fetch_page`.

    `fetch_page(page_num)` issues the actual HTTP request for a given 1-indexed
    page. `pluck(response)` extracts the typed list from the response envelope
    (e.g. `lambda r: r.trips`). When the response has no `max_page` we treat it
    as a single-page result.
    """
    page = 1
    while True:
        response = fetch_page(page)
        yield from pluck(response)
        max_page = response.max_page or 1
        if page >= max_page:
            return
        page += 1
