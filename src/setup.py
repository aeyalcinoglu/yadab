import asyncio
from helpers.initialize import setup
from models.data import Data


async def _main():
    await setup(reload_healthy=True)

if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.run_until_complete(_main())

    assert Data.lines is not None
    assert Data.address_data is not None
    assert Data.pricing_contracts is not None
    assert Data.factories is not None
