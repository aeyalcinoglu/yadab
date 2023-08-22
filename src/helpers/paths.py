import os
import time
import json
import asyncio
from collections import defaultdict
from itertools import product
from models.market import Path
from models.data import Data
from helpers.price import (direct_initialization_prices,
                           reverse_initialization_prices)


async def get_pair_address_from_path(path: Path) -> str:
    """
    Returns the pair address for a given path.
    """
    return await asyncio.gather(
        *[path.dex.factory.getPair.coroutine(
            path.from_token.address,
            path.to_token.address)])


async def generate_healthy_pairs() -> None:
    """
    Generates all possible pairs of tokens.
    """
    start_time = time.perf_counter()
    script_dir = os.path.dirname(os.path.abspath(__file__))
    pairs_file = os.path.join(script_dir, 'assets', 'healthy_pairs.json')
    v2_paths = Path.get_all_v2_paths()

    pair_addresses = await asyncio.gather(
        *[get_pair_address_from_path(path) for path in v2_paths])
    pair_addresses = [pair_address[0] for pair_address in pair_addresses]
    indexed_pair_addresses = dict(zip([str(path) for path in v2_paths],
                                      pair_addresses))
    with open(pairs_file, "w") as file:
        json.dump(indexed_pair_addresses, file, indent=4)

    end_time = time.perf_counter()
    print("Generated healthy_pairs.json in {} seconds".format(
        end_time - start_time))


def load_healthy_pair_names() -> list[Path]:
    """
    Loads the healthy paths from the file 'healthy_paths'.
    """
    script_dir = os.path.dirname(os.path.abspath(__file__))
    paths_file = os.path.join(script_dir, 'assets', 'healthy_pairs.json')

    with open(paths_file, 'r') as file:
        healthy_pair_names = json.load(file)
        pair_names = {}
        for path_name, pair_address in healthy_pair_names.items():
            pair_names[path_name] = pair_address

    return pair_names


def generate_all_paths() -> list[Path]:
    """
    Generates all possible paths.
    """
    all_paths = []
    for dex in Data.get_dex_names():
        for to_token, from_token in product(Data.get_token_names(), repeat=2):
            if to_token != from_token:
                all_paths.append(Path.get_path_from_name(dex,
                                                         from_token,
                                                         to_token))

    return all_paths


async def generate_healthy_path_names() -> None:
    """
    Generate the list of path names which pass pricing calculation successfully.
    Write them to the file 'healthy_paths'
    """
    start_time = time.perf_counter()
    script_dir = os.path.dirname(os.path.abspath(__file__))
    paths_file = os.path.join(script_dir, 'assets', 'healthy_paths')
    base_amount_in = 100
    all_paths = generate_all_paths()
    path_count = len(all_paths)

    with open(paths_file, "w") as file:
        path_results = (await asyncio.gather(
            *[direct_initialization_prices(all_paths,
                                           [base_amount_in]*path_count)]))[0]
        reverse_results = (await asyncio.gather(
            *[reverse_initialization_prices(all_paths,
                                            [base_amount_in]*path_count)]))[0]
        for path, price in path_results.items():
            if price > base_amount_in / 3 and price < base_amount_in * 3:
                if reverse_results[path] > base_amount_in / 2 and reverse_results[path] < base_amount_in * 2:
                    file.write("{}\n".format(str(path)))

    end_time = time.perf_counter()
    print("Generated healthy_paths in {} seconds".format(
        end_time - start_time))


def load_healthy_path_names() -> list[str]:
    """
    Loads the healthy paths from the file 'healthy_paths'.
    """
    script_dir = os.path.dirname(os.path.abspath(__file__))
    paths_file = os.path.join(script_dir, 'assets', 'healthy_paths')

    with open(paths_file, 'r') as file:
        return [path.strip() for path in file.readlines()]


def generate_healthy_loop_names() -> None:
    """
    Generate the list of loop names via composition of healthy paths.
    Write them to the file 'healthy_loops.json'
    """
    start_time = time.perf_counter()
    script_dir = os.path.dirname(os.path.abspath(__file__))
    loops_file = os.path.join(script_dir, 'assets', 'healthy_loops.json')
    healthy_path_names = load_healthy_path_names()
    loops = defaultdict(list)

    print('In total there are {} healthy paths.'.format(len(healthy_path_names)))

    for path_name in healthy_path_names:
        path_dex_name, path_from_token_name, path_to_token_name = path_name.split(
            ' ')
        for candidate_dex_name in Data.get_dex_names():
            candidate_path_name = "{} {} {}".format(candidate_dex_name,
                                                    path_to_token_name,
                                                    path_from_token_name)
            if candidate_dex_name != path_dex_name \
                    and candidate_path_name in healthy_path_names:
                loops[path_name].append(candidate_path_name)

    with open(loops_file, "w") as file:
        json.dump(loops, file, indent=4)

    end_time = time.perf_counter()
    print("Generated healthy_loops.json in {} seconds".format(
        end_time - start_time))


def load_healthy_loops() -> dict[Path, list[Path]]:
    """
    Loads the healthy loops from the file 'healthy_loops.json'.
    """
    script_dir = os.path.dirname(os.path.abspath(__file__))
    loops_file = os.path.join(script_dir, 'assets', 'healthy_loops.json')

    with open(loops_file, 'r') as file:
        healthy_loop_names = json.load(file)
        loops = {}
        for forward_path_name, backward_path_names in healthy_loop_names.items():
            forward_path = Path.get_path_from_name(
                *forward_path_name.split(' '))
            backward_paths = [Path.get_path_from_name(*backward_path_name.split(' '))
                              for backward_path_name in backward_path_names]
            loops[forward_path] = backward_paths
    return loops


def generate_healthy_triangle_names() -> None:
    """
    Generate the list of triangle names via composition of healthy paths.
    Write them to the file 'healthy_triangles.json'
    """
    start_time = time.perf_counter()

    script_dir = os.path.dirname(os.path.abspath(__file__))
    triangles_file = os.path.join(
        script_dir, 'assets', 'healthy_triangles.json')
    healthy_path_names = load_healthy_path_names()
    path_names = [path_name.split(' ') for path_name in healthy_path_names]
    left_map = defaultdict(list)
    right_map = defaultdict(list)
    triangles = defaultdict(lambda: defaultdict(list))

    for middle_path_name in path_names:
        path_dex_name, path_from_token_name, path_to_token_name = middle_path_name
        left_map[path_from_token_name].append(middle_path_name)
        right_map[path_to_token_name].append(middle_path_name)

    for middle_path_name in path_names:
        for left_path_name in right_map[middle_path_name[1]]:
            for right_path_name in left_map[middle_path_name[2]]:
                if left_path_name[1] == right_path_name[2]:
                    triangles[' '.join(middle_path_name)][' '.join(left_path_name)].append(
                        ' '.join(right_path_name))

    with open(triangles_file, "w") as file:
        json.dump(triangles, file, indent=4)

    end_time = time.perf_counter()
    print("Generated healthy_triangles.json in {} seconds".format(
        end_time - start_time))
    return triangles


def load_healthy_triangles() -> dict[Path, dict[Path, Path]]:
    """
    Loads the healthy triangles from the file 'healthy_triangles.json'.
    """
    script_dir = os.path.dirname(os.path.abspath(__file__))
    triangles_file = os.path.join(
        script_dir, 'assets', 'healthy_triangles.json')

    with open(triangles_file, 'r') as file:
        healthy_triangle_names = json.load(file)
        triangles = defaultdict(lambda: defaultdict(list))
        for middle_path_name, ear_paths in healthy_triangle_names.items():
            for left_path_name, right_path_names in ear_paths.items():
                for right_path_name in right_path_names:
                    middle_path = Path.get_path_from_name(
                        *middle_path_name.split(' '))
                    left_path = Path.get_path_from_name(
                        *left_path_name.split(' '))
                    right_path = Path.get_path_from_name(
                        *right_path_name.split(' '))
                    triangles[middle_path][left_path].append(right_path)

    return triangles
