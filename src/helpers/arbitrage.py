import asyncio
from collections import defaultdict
from models.market import Path
from helpers.price import (direct_prices,
                           direct_indexed_prices,
                           reverse_prices)
from helpers.utility import (fill_missing_triangles,
                             get_remaning_paths)


async def calculate_arbitrage(lines: dict[Path, list[Path]],
                              triangles: dict[Path, dict[Path, Path]],
                              amount_in: float):
    """
    Calculate the arbitrage for a given amount_in and triangles.
    """
    new_triangles = fill_missing_triangles(triangles)
    middle_paths = list(new_triangles.keys())
    remaining_paths, start_index, end_index = get_remaning_paths(middle_paths,
                                                                 lines.keys())

    initial_results = (await asyncio.gather(
        asyncio.gather(
            *[direct_prices(middle_paths + remaining_paths,
                            [amount_in] * end_index)],
            *[reverse_prices(middle_paths, [amount_in] * start_index)])
    ))[0]

    whole_direct_results = initial_results[0]
    right_results = initial_results[1]
    paths_of_connection_hit_targets = []
    amounts_of_connection_hit_targets = []
    for middle_path in middle_paths:
        for left_path in new_triangles[middle_path].keys():
            paths_of_connection_hit_targets.append((3, left_path, middle_path))
            amounts_of_connection_hit_targets.append(
                whole_direct_results[left_path])

    start_index = len(paths_of_connection_hit_targets)
    for forward_path in lines.keys():
        for backward_path in lines[forward_path]:
            paths_of_connection_hit_targets.append((2, forward_path,
                                                    backward_path))
            amounts_of_connection_hit_targets.append(
                whole_direct_results[forward_path])

    final_amount_outs = (await asyncio.gather(
        *[direct_indexed_prices(paths_of_connection_hit_targets,
                                amounts_of_connection_hit_targets)]))[0]

    line_outs = defaultdict(int)
    triangular_outs = defaultdict(int)
    for (n, left_path, middle_path), price in final_amount_outs:
        if n == 2:
            line_outs[(left_path, middle_path)] = price
        if n == 3:
            triangular_outs[(left_path, middle_path)] = price

    triangular_arbitrage_results = []
    for middle_path in middle_paths:
        for left_path in new_triangles[middle_path].keys():
            for right_path in new_triangles[middle_path][left_path]:
                arbitrage_result = triangular_outs[(left_path,
                                                    middle_path)] - right_results[right_path]
                if right_results[right_path] <= 0 or triangular_outs[(left_path, middle_path)] <= 0:
                    arbitrage_result = float("-inf")
                triangular_arbitrage_results.append(
                    (left_path,
                     middle_path,
                     right_path,
                     arbitrage_result))

    line_arbitrage_results = []
    for (forward_path, backward_path), price in line_outs.items():
        line_arbitrage_results.append(
            (forward_path, backward_path, price - amount_in))

    return line_arbitrage_results, triangular_arbitrage_results
