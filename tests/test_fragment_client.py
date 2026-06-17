import pytest
from unittest.mock import AsyncMock, patch
from tg_gifts_sdk.fragment import FragmentClient
from tg_gifts_sdk.models import Listing, FloorStats

# Mock HTML response from Fragment API
MOCK_HTML = '''
<div class="tm-grid">
    <a class="tm-grid-item" href="/gift/pepe_1">
        <span class="item-name">Plush Pepe</span>
        <span class="item-num">#123</span>
        <span class="tm-grid-item-value icon-ton"> 10.5 TON </span>
        <span class="tm-grid-item-status">Active</span>
        <time datetime="2026-06-17T12:00:00Z">June 17</time>
    </a>
    <a class="tm-grid-item" href="/gift/pepe_2">
        <span class="item-name">Plush Pepe</span>
        <span class="item-num">#456</span>
        <span class="tm-grid-item-value icon-ton"> 8.2 TON </span>
        <span class="tm-grid-item-status">Active</span>
        <time datetime="2026-06-17T12:05:00Z">June 17</time>
    </a>
    <a class="tm-grid-item" href="/gift/cat_1">
        <span class="item-name">Cool Cat</span>
        <span class="item-num">#789</span>
        <span class="tm-grid-item-value icon-ton"> 5.0 TON </span>
        <span class="tm-grid-item-status">Active</span>
        <time datetime="2026-06-17T12:10:00Z">June 17</time>
    </a>
</div>
'''

@pytest.mark.asyncio
async def test_fetch_listings_parsing():
    client = FragmentClient(auth_data="test_auth")
    
    with patch('tg_gifts_sdk.fragment.post_json', new_callable=AsyncMock) as mock_post:
        mock_post.return_value = (200, {"html": MOCK_HTML})
        
        listings = await client.fetch_listings(gift_name="Plush Pepe")
        
        assert len(listings) == 3
        assert listings[0].gift_name == "Plush Pepe #123"
        assert listings[0].price == 10.5
        assert listings[1].gift_name == "Plush Pepe #456"
        assert listings[1].price == 8.2
        assert listings[2].gift_name == "Cool Cat #789"
        assert listings[2].price == 5.0

@pytest.mark.asyncio
async def test_fetch_floor_stats():
    client = FragmentClient(auth_data="test_auth")
    
    with patch('tg_gifts_sdk.fragment.post_json', new_callable=AsyncMock) as mock_post:
        mock_post.return_value = (200, {"html": MOCK_HTML})
        
        stats = await client.fetch_floor_stats()
        
        stats_dict = {s.collection: s.floor for s in stats}
        
        assert "Plush Pepe" in stats_dict
        assert stats_dict["Plush Pepe"] == 8.2
        assert "Cool Cat" in stats_dict
        assert stats_dict["Cool Cat"] == 5.0
