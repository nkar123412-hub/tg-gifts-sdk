
"""Fragment marketplace client — async, read-only.

Reverse-engineered against Fragment's gift listings API.
Uses curl_cffi Firefox impersonation to satisfy CloudFlare TLS fingerprinting.

Read-only scope:
- Listings (search)
- Floor stats (derived from listings)
"""
from __future__ import annotations

import asyncio
import json
import re
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from tg_gifts_sdk._http import build_firefox_headers, post_json
from tg_gifts_sdk.exceptions import (
    AuthDataMissingError,
    MarketplaceUnavailableError,
)
from tg_gifts_sdk.models import FloorStats, Listing

if TYPE_CHECKING:
    from types import TracebackType

FRAGMENT_API_BASE = "https://fragment.com/api"
FRAGMENT_ORIGIN = "https://fragment.com"
FRAGMENT_HOST = "fragment.com"

# Regexes from pyfragment for HTML parsing
GRID_ITEM_RE = re.compile(r'<a\b[^>]*class="[^"]*tm-grid-item[^"]*"[^>]*>(.*?)</a>', re.DOTALL)
GRID_HREF_RE = re.compile(r'href="(/gift/([^?"]+))"')
GRID_NAME_RE = re.compile(r'class="item-name">([^<]+)<')
GRID_NUM_RE = re.compile(r'class="item-num">[^#]*#(\w+)<')
GRID_PRICE_RE = re.compile(r'class="[^"]*tm-grid-item-value[^"]*icon-ton[^"]*"[^>]*>\s*([0-9][^<]*?)\s*<')
GRID_STATUS_RE = re.compile(r'class="[^"]*tm-grid-item-status[^"]*"[^>]*>\s*([^<]+?)\s*<')
GRID_DATETIME_RE = re.compile(r'<time[^>]+datetime="([^"]+)"')

def _parse_listing(item_html: str) -> Listing | None:
    """Parse a single HTML block of a Fragment gift listing into a Listing object."""
    try:
        href_m = GRID_HREF_RE.search(item_html)
        if not href_m:
            return None
        slug = href_m.group(1).lstrip("/")
        
        name_m = GRID_NAME_RE.search(item_html)
        num_m = GRID_NUM_RE.search(item_html)
        item_name = name_m.group(1).strip() if name_m else slug
        item_num = f" #{num_m.group(1)}" if num_m else ""
        name = f"{item_name}{item_num}"
        
        price_m = GRID_PRICE_RE.search(item_html)
        price_val = 0.0
        if price_m:
            raw_price = price_m.group(1).strip().replace(",", "")
            try:
                price_val = float(raw_price)
            except ValueError:
                pass

        return Listing(
            marketplace="fragment",
            gift_id=0, # Fragment uses slugs, we might need to resolve slug -> id
            gift_name=name,
            gift_num=0,
            model=None,
            backdrop=None,
            symbol=None,
            price=price_val,
            asset="TON",
            seller=None,
            raw={"slug": slug},
        )
    except Exception:
        return None

class FragmentClient:
    """Async read-only client for the Fragment marketplace."""

    def __init__(
        self,
        *,
        auth_data: str,
        timeout: float = 30.0,
        proxy: str | None = None,
        max_concurrent: int = 4,
        max_retries: int = 2,
    ) -> None:
        self.auth_data = auth_data
        self.timeout = timeout
        self.proxy = proxy
        self.max_retries = max_retries
        self._semaphore = asyncio.Semaphore(max_concurrent)

    async def __aenter__(self) -> FragmentClient:
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        await self.aclose()

    async def aclose(self) -> None:
        return None

    async def fetch_listings(
        self,
        *,
        gift_name: str | None = None,
        model: str | None = None,
        backdrop: str | None = None,
        symbol: str | None = None,
        sort: str = "price_asc",
        limit: int = 30,
        page: int = 1,
        asset: str = "TON",
    ) -> list[Listing]:
        self._require_auth()
        
        # Fragment uses a different API structure than Tonnel.
        # Based on pyfragment, we send a request to "searchAuctions".
        payload = {
            "type": "gifts",
            "query": gift_name or "",
            "offset": page * limit,
            "limit": limit,
            "sort": "price_asc" if sort == "price_asc" else "price_desc",
            "user_auth": self.auth_data,
        }

        async with self._semaphore:
            status, body = await post_json(
                f"{FRAGMENT_API_BASE}/searchAuctions",
                json_body=payload,
                headers=build_firefox_headers(origin=FRAGMENT_ORIGIN, host=FRAGMENT_HOST),
                timeout=self.timeout,
                proxy=self.proxy,
                max_retries=self.max_retries,
            )

        if status != 200:
            raise MarketplaceUnavailableError(
                marketplace="fragment",
                status_code=status,
                body=str(body),
            )

        if isinstance(body, dict) and "html" in body:
            html_content = body["html"]
        elif isinstance(body, str):
            html_content = body
        else:
            html_content = ""

        listings: list[Listing] = []
        # We use the GRID_ITEM_RE to find all listing blocks in the HTML
        import re
        for item_html in GRID_ITEM_RE.finditer(html_content):
            parsed = _parse_listing(item_html.group(0))
            if parsed is not None:
                listings.append(parsed)
        
        return listings

    async def fetch_floor_stats(self) -> list[FloorStats]:
        # Fragment doesn't have a direct floor API. 
        # We implement it by fetching the first page of listings sorted by price_asc.
        listings = await self.fetch_listings(sort="price_asc", limit=100)
        
        # Group by gift_name to find the floor for each
        floors: dict[str, float] = {}
        for l in listings:
            name = l.gift_name
            if name not in floors or l.price < floors[name]:
                floors[name] = l.price
        
        return [
            FloorStats(
                marketplace="fragment",
                collection=name,
                floor=price,
                models={},
                backdrops={},
                symbols={},
            )
            for name, price in floors.items()
        ]

    def _require_auth(self) -> None:
        if not self.auth_data:
            raise AuthDataMissingError(
                "FragmentClient requires auth_data — see README for how to capture "
                "initData from Fragment's localStorage."
            )
