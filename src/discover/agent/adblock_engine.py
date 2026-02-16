"""Brave adblock engine with EasyList, cached to disk."""

import urllib.request
from pathlib import Path

from adblock import Engine, FilterSet

EASYLIST_URL = "https://raw.githubusercontent.com/easylist/easylist/gh-pages/easylist.txt"
CACHE_DIR = Path.home() / ".cache" / "discourse-kg"
CACHE_FILE = CACHE_DIR / "easylist_engine.dat"
_engine: Engine | None = None

# CSS selectors for ad-related DOM elements (used with excluded_selector)
EXCLUDED_SELECTOR = (
    "aside, .sidebar, .advertisement, .ads, .ad-container, "
    '[id*="ad-"], [class*="banner"], .social-share, .menu, .breadcrumb'
)


def _fetch_and_build() -> Engine:
    """Fetch EasyList and build engine."""
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    filters = FilterSet(debug=False)
    with urllib.request.urlopen(EASYLIST_URL, timeout=30) as resp:
        filters.add_filter_list(resp.read().decode(), "standard")
    return Engine(filters, optimize=True)


def _load_engine() -> Engine:
    """Load engine from cache or fetch+build."""
    global _engine
    if _engine is not None:
        return _engine
    if CACHE_FILE.exists():
        try:
            engine = Engine(FilterSet(debug=False))
            engine.deserialize_from_file(str(CACHE_FILE))
            _engine = engine
            return engine
        except Exception:
            pass
    engine = _fetch_and_build()
    engine.serialize_to_file(str(CACHE_FILE))
    _engine = engine
    return engine


def get_engine() -> Engine:
    """Return cached adblock engine (loads on first call)."""
    return _load_engine()


async def setup_blocking(context) -> None:
    """Register route handler to block ads/trackers matching EasyList."""
    engine = get_engine()

    async def route_handler(route):
        request = route.request
        source_url = request.frame.url if request.frame else ""
        try:
            if engine.check_network_urls(request.url, source_url, request.resource_type).matched:
                await route.abort()
                return
        except Exception:
            pass
        await route.continue_()

    await context.route("**/*", route_handler)
