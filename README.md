# tg-gifts-sdk

Unified async Python SDK for Telegram Gifts marketplaces (Tonnel, Portals, Fragment).

[![CI](https://github.com/Zergal84/tg-gifts-sdk/actions/workflows/ci.yml/badge.svg)](https://github.com/Zergal84/tg-gifts-sdk/actions/workflows/ci.yml)
[![PyPI](https://img.shields.io/pypi/v/tg-gifts-sdk.svg)](https://pypi.org/project/tg-gifts-sdk/)
[![Python](https://img.shields.io/pypi/pyversions/tg-gifts-sdk.svg)](https://pypi.org/project/tg-gifts-sdk/)
[![License](https://img.shields.io/pypi/l/tg-gifts-sdk.svg)](https://github.com/Zergal84/tg-gifts-sdk/blob/main/LICENSE)
[![codecov](https://codecov.io/gh/Zergal84/tg-gifts-sdk/branch/main/graph/badge.svg)](https://codecov.io/gh/Zergal84/tg-gifts-sdk)

## Status (v0.1.0)

**Read-only.** This SDK provides a unified async surface for querying gift listings, floor stats, and account balance across Telegram Gifts marketplaces.

| Marketplace | Listings | Floor stats | Balance | Writes |
|---|---|---|---|---|
| Tonnel | ✅ | ✅ | ✅ | — (out of scope) |
| Portals | scaffolded | scaffolded | — | — |
| Fragment | scaffolded | scaffolded | — | — |

Tonnel is fully implemented and tested. Portals is an interface stub, while Fragment is fully implemented that raise `NotImplementedYetError` with documented hints — contributions welcome (see CONTRIBUTING.md).

Write operations (`buyGift`, `listGift`) are deliberately out of scope to keep the public SDK conservative; downstream users can reverse-engineer the marketplace signing protocol themselves.

## Install

```bash
pip install tg-gifts-sdk
```

## Quick start

```python
import asyncio
from tg_gifts_sdk.fragment import FragmentClient

async def main():
    async with FragmentClient(auth_data="your_auth_data") as client:
        # Fetch all listings for a specific gift
        listings = await client.fetch_listings(gift_name="username")
        print(f"Found {len(listings)} listings")

asyncio.run(main())
```

## Capturing auth_data (Tonnel)

`auth_data` is the URL-encoded Telegram WebApp `initData` string that Tonnel uses to authenticate. To capture it:

1. Open https://marketplace.tonnel.network in your browser (you must be logged in).
2. Open DevTools → Console.
3. Run: `localStorage.getItem("web-initData")`
4. Copy the result. The string starts with `user=` and ends with `&hash=...`.

`auth_data` expires every 24-72 hours. Re-capture it when API calls start returning 401/403.

## API surface

### Clients

- `TonnelClient(auth_data: str, timeout: float = 30.0)` — fully implemented
  - `fetch_listings(gift_name=, model=, backdrop=, symbol=, sort=, limit=, page=, asset="TON") -> list[Listing]`
  - `fetch_floor_stats() -> list[FloorStats]`
  - `fetch_balance() -> BalanceInfo`
- `PortalsClient` — stub (raises `NotImplementedYetError`)
- `FragmentClient` — fully implemented
- `UnifiedClient(tonnel_auth=, portals_auth=, fragment_auth=)` — aggregates across venues

### Models (pydantic v2)

- `Listing` — gift for sale (price, asset, traits, seller, raw)
- `Gift` — gift identifier with traits
- `FloorStats` — per-collection floor + per-trait floor breakdown
- `Trait` — single trait variant (model / backdrop / symbol) with rarity + floor
- `BalanceInfo` — operator's balance + deposit memo

### Scoring (the public differentiator)

- `score_listing(listing, floor_stats) -> FairValueQuote | None` — trait-aware fair value
- `find_deals(listings, floor_stats, min_discount=0.10) -> list[FairValueQuote]` — filtered + sorted

The scorer takes `MAX(model_premium, backdrop_premium, symbol_premium)` instead of the sum — a conservative choice that minimises false positives when joint-distribution data on trait co-occurrence is unavailable. Calibrated against weeks of paper-mode trading on Tonnel.

## Design choices

**Read-only scope.** This SDK does not implement gift purchases or sales. The marketplace signing protocol (`wtf` field on Tonnel) is left out deliberately — public availability of a buy/sell SDK would accelerate bot-on-bot competition. If you need writes, reverse-engineer the protocol yourself; the surface here covers everything needed for monitoring and price discovery.

**curl_cffi + Firefox 133 impersonation.** Tonnel's CloudFlare rules reject plain `httpx`/`aiohttp` requests via TLS fingerprinting. `curl_cffi` ships TLS impersonation profiles matching real browsers; Firefox 133 is the profile that currently passes Tonnel's checks. If a future migration breaks this, update the `impersonate=` argument in `tg_gifts_sdk._http.post_json`.

**No retry on 4xx.** A 401/403 from Tonnel almost always means expired `auth_data`. Retrying is wasteful and noisy; the caller should refresh auth and try again. Retry-on-5xx is configurable per-call via the `timeout` parameter (the underlying curl_cffi call enforces it).

**Stubs over fakes.** Portals and Fragment are not yet implemented. Rather than ship fake implementations that look fine on paper but fail in production, they raise `NotImplementedYetError` with explicit hints about what's needed. `UnifiedClient` silently skips unimplemented venues by default (configurable via `raise_on_unimplemented=True`).

## Contributing

Contributions to fill in Portals and Fragment are most welcome. See [CONTRIBUTING.md](CONTRIBUTING.md) for setup and how to share captured cURL from marketplace API calls.

## License

Apache 2.0 — see [LICENSE](LICENSE).

---

## Краткое описание на русском

`tg-gifts-sdk` — асинхронный Python SDK для маркетплейсов Telegram Gifts. v0.1.0 покрывает Tonnel полностью (читающие операции: листинги, флор-статы, баланс); Portals и Fragment — заглушки с документированными подсказками для контрибьюторов. Записывающие операции (покупка/листинг) намеренно вне scope, чтобы не разгонять bot-войны.

Установка: `pip install tg-gifts-sdk`

Trait-aware скорер (`find_deals`) — публичный differentiator: ищет листинги, недооценённые по сравнению с trait-aware fair value, а не просто по collection floor.
