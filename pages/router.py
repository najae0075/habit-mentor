"""Small, testable page dispatcher."""

from collections.abc import Callable, Mapping


PageRenderer = Callable[[], None]


def render_page(page: str, routes: Mapping[str, PageRenderer], default: PageRenderer) -> None:
    routes.get(page, default)()
