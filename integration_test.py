import asyncio
from tg_gifts_sdk.fragment import FragmentClient

async def run_test():
    print('Initializing FragmentClient...')
    client = FragmentClient()
    print('Fetching listings for a test collection (username)...')
    try:
        listings = await client.fetch_listings(gift_name='username')
        print(f'Found {len(listings)} listings.')
        if listings:
            print('Sample listing:', listings[0])
        else:
            print('No active listings found, but the request succeeded.')
    except Exception as e:
        print(f'Integration test failed: {e}')
        exit(1)

if __name__ == '__main__':
    asyncio.run(run_test())
