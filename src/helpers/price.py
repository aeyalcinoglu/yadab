import asyncio
from models.market import Path
from models.data import Data


def direct_sync_price(path: Path, amount_in: float) -> float:
    """
    Syncronous wrapper for both v2 and v3.
    Forward direction.
    """
    local_amount_in = path.from_token.get_relative_price(amount_in)
    try:
        if path.dex.name.endswith("v3"):
            amount_out = path.dex.pricing_contract.quoteExactInputSingle.call(
                (
                    path.from_token.address,
                    path.to_token.address,
                    local_amount_in,
                    3000,
                    0
                )
            )[0]
        else:
            amount_out = path.dex.pricing_contract.getAmountsOut(local_amount_in,
                                                                 path.get_address_path())[1]
        return path.to_token.recover_original_price(amount_out)
    except:
        return 0


def reverse_sync_price(path: Path, amount_out: float) -> float:
    """
    Syncronous wrapper for both v2 and v3.
    Reverse direction.
    """
    local_amount_out = path.to_token.get_relative_price(amount_out)
    try:
        if path.dex.name.endswith("v3"):
            amount_in = path.dex.pricing_contract.quoteExactOutputSingle.call(
                (
                    path.from_token.address,
                    path.to_token.address,
                    local_amount_out,
                    3000,
                    0
                )
            )
            amount_in = amount_in[0]
        else:
            amount_in = path.dex.pricing_contract.getAmountsIn(local_amount_out,
                                                               path.get_address_path())[0]
        return path.from_token.recover_original_price(amount_in)
    except:
        return 0


def get_amount_out(amount_in: float,
                   reserve_in: float,
                   reserve_out: float) -> float:
    """
    Simulates v2's router.getAmountsOut() function.
    https://github.com/Uniswap/v2-periphery/blob/master/contracts/libraries/UniswapV2Library.sol#L43
    """
    amount_in_with_fee = amount_in * (997)
    numerator = amount_in_with_fee * reserve_out
    denominator = (reserve_in * 1000) + amount_in_with_fee
    return numerator // denominator


def get_amount_in(amount_out: float,
                  reserve_in: float,
                  reserve_out: float) -> float:
    """
    Simulates v2's router.getAmountsIn() function.
    """
    numerator = reserve_in * amount_out * 1000
    denominator = (reserve_out - amount_out) * 997
    return numerator // denominator + 1


async def get_v2_reserves(path: Path) -> tuple[float,
                                               tuple[float, float]]:
    """
    Gets the reserves for a given path.
    """
    pair = Data.pairs[str(path)]
    reserve_result = await asyncio.gather(*[pair.getReserves.coroutine()])
    default_direction = int(path.from_token.address, 16) < \
        int(path.to_token.address, 16)
    r1, r2, _ = reserve_result[0]
    if not default_direction:
        (r1, r2) = (r2, r1)

    return (path, (r1, r2))


async def update_v2_reserves() -> None:
    """
    Updates the reserves for all v2 paths.
    """
    reserves = (await asyncio.gather(
        *[get_v2_reserves(path) for path in Path.get_all_v2_paths()]))

    Data.reserves = {path: reserve
                     for path, reserve in reserves}


def direct_V2_reserve_price(path: Path, amount_in: float) -> float:
    """
    Uses the reserves to calculate the price for a given amount_in and path.
    """
    r1, r2 = Data.reserves[path]
    local_amount_in = path.from_token.get_relative_price(amount_in)
    amount_out = get_amount_out(local_amount_in, r1, r2)
    return path.to_token.recover_original_price(amount_out)


def reverse_V2_reserve_price(path: Path, amount_out: float) -> float:
    """
    Uses the reserves to calculate the price for a given amount_out and path.
    """
    r1, r2 = Data.reserves[path]
    local_amount_out = path.to_token.get_relative_price(amount_out)
    amount_in = get_amount_in(local_amount_out, r1, r2)
    return path.from_token.recover_original_price(amount_in)


async def direct_V2_price(path: Path, amount_in: float) -> float:
    """
    Returns the exact quote for a given amount_in and path.
    For v2, uses dank_mid's multicall to make the calculations.
    """
    price_to_be = await asyncio.gather(
        *[path.dex.pricing_contract.
            getAmountsOut.coroutine(
                path.from_token.get_relative_price(amount_in),
                path.get_address_path())])
    try:
        return path.to_token.recover_original_price(price_to_be[0][1])
    except:
        return 0


async def direct_V3_price(path: Path, amount_in: float) -> float:
    """
    Returns the exact quote for a given amount_in and path.
    For v3, uses dank_mid's multicall to make the calculations.
    """
    price_to_be = await asyncio.gather(
        *[path.dex.pricing_contract.
            quoteExactInputSingle.coroutine((
                path.from_token.address,
                path.to_token.address,
                path.from_token.get_relative_price(amount_in),
                path.dex.fee,
                0))])
    try:
        return path.to_token.recover_original_price(price_to_be[0][0])
    except:
        return 0


async def reverse_V2_price(path: Path, amount_out: float) -> float:
    """
    Returns the exact quote for a given amount_out and path.
    For v3, uses dank_mid's multicall to make the calculations.
    """
    price_to_be = await asyncio.gather(
        *[path.dex.pricing_contract.
            getAmountsIn.coroutine(
                path.to_token.get_relative_price(amount_out),
                path.get_address_path())])
    try:
        return path.from_token.recover_original_price(price_to_be[0][0])
    except:
        return 0


async def reverse_V3_price(path: Path, amount_out: float) -> float:
    """
    Returns the exact quote for a given amount_out and path.
    For v3, uses dank_mid's multicall to make the calculations.
    """
    price_to_be = await asyncio.gather(
        *[path.dex.pricing_contract.
            quoteExactOutputSingle.coroutine((
                path.from_token.address,
                path.to_token.address,
                path.to_token.get_relative_price(amount_out),
                path.dex.fee,
                0))])
    try:
        return path.from_token.recover_original_price(price_to_be[0][0])
    except:
        return 0


async def direct_prices(paths: list[Path],
                        amount_ins: list[float]) -> dict[Path, float]:
    """
    Returns the exact quote for a list of amount_in and path pairs.
    """
    assert len(paths) == len(amount_ins)

    filled_paths = [(path, amount_in)
                    for path, amount_in in zip(paths, amount_ins)]

    v2_paths = [(path, amount_in) for (path, amount_in)
                in filled_paths if path.dex.name.endswith("v2")]
    v3_paths = [(path, amount_in) for (path, amount_in)
                in filled_paths if path.dex.name.endswith("v3")]

    v2_prices = [direct_V2_reserve_price(path, amount_in)
                 for (path, amount_in) in v2_paths]
    v3_prices = await asyncio.gather(
        *[direct_V3_price(path, amount_in) for (path, amount_in) in v3_paths])

    amount_outs = {
        path:
        price for (path, _), price in
        zip(v2_paths + v3_paths, v2_prices + v3_prices)}

    return amount_outs


async def reverse_prices(paths: list[Path],
                         amount_ins: list[float]) -> dict[Path, float]:
    """
    Returns the exact quote for a list of amount_in and path pairs.
    """
    assert len(paths) == len(amount_ins)

    filled_paths = [(path, amount_in)
                    for path, amount_in in zip(paths, amount_ins)]

    v2_paths = [(path, amount_in) for (path, amount_in)
                in filled_paths if path.dex.name.endswith("v2")]
    v3_paths = [(path, amount_in) for (path, amount_in)
                in filled_paths if path.dex.name.endswith("v3")]

    v2_prices = [reverse_V2_reserve_price(path, amount_in)
                 for (path, amount_in) in v2_paths]
    v3_prices = await asyncio.gather(
        *[reverse_V3_price(path, amount_in) for (path, amount_in) in v3_paths])

    amount_outs = {
        path:
        price for (path, _), price in
        zip(v2_paths + v3_paths, v2_prices + v3_prices)}

    return amount_outs


async def direct_initialization_prices(paths: list[Path],
                                       amount_ins: list[float]) -> dict[Path, float]:
    """
    Similar to direct_prices but doesn't use reserves.
    """
    assert len(paths) == len(amount_ins)

    filled_paths = [(path, amount_in)
                    for path, amount_in in zip(paths, amount_ins)]

    v2_paths = [(path, amount_in) for (path, amount_in)
                in filled_paths if path.dex.name.endswith("v2")]
    v3_paths = [(path, amount_in) for (path, amount_in)
                in filled_paths if path.dex.name.endswith("v3")]

    prices = await asyncio.gather(
        *[direct_V2_price(path, amount_in)
          for (path, amount_in) in v2_paths],
        *[direct_V3_price(path, amount_in) for (path, amount_in) in v3_paths])

    amount_outs = {
        path:
        price for (path, _), price in
        zip(v2_paths + v3_paths, prices)}

    return amount_outs


async def reverse_initialization_prices(paths: list[Path],
                                        amount_ins: list[float]) -> dict[Path, float]:
    """
    Similar to reverse_prices but doesn't use reserves.
    """
    assert len(paths) == len(amount_ins)

    filled_paths = [(path, amount_in)
                    for path, amount_in in zip(paths, amount_ins)]

    v2_paths = [(path, amount_in) for (path, amount_in)
                in filled_paths if path.dex.name.endswith("v2")]
    v3_paths = [(path, amount_in) for (path, amount_in)
                in filled_paths if path.dex.name.endswith("v3")]

    prices = await asyncio.gather(
        *[reverse_V2_price(path, amount_in)
          for (path, amount_in) in v2_paths],
        *[reverse_V3_price(path, amount_in) for (path, amount_in) in v3_paths])

    amount_outs = {
        path:
        price for (path, _), price in
        zip(v2_paths + v3_paths, prices)}

    return amount_outs


async def direct_indexed_prices(paths: list[Path],
                                amount_ins: list[float]) -> dict[tuple[Path, Path],
                                                                 float]:
    """
    Similar to direct_prices but parsing made easy for triangular arbitrage.
    """
    assert len(paths) == len(amount_ins)

    filled_paths = [(n, left_path, middle_path, amount_in)
                    for (n, left_path, middle_path), amount_in in zip(paths, amount_ins)]

    v2_paths = [(n, left_path, middle_path, amount_in) for (n, left_path, middle_path, amount_in)
                in filled_paths if middle_path.dex.name.endswith("v2")]
    v3_paths = [(n, left_path, middle_path, amount_in) for (n, left_path, middle_path, amount_in)
                in filled_paths if middle_path.dex.name.endswith("v3")]

    v2_prices = [direct_V2_reserve_price(middle_path, amount_in)
                 for (n, left_path, middle_path, amount_in) in v2_paths]
    v3_prices = await asyncio.gather(
        *[direct_V3_price(middle_path, amount_in) for (n, left_path, middle_path, amount_in) in v3_paths])

    amount_outs = [
        ((n, left_path, middle_path), price) for (n, left_path, middle_path, amount_in), price in
        zip(v2_paths + v3_paths, v2_prices + v3_prices)]

    return amount_outs
