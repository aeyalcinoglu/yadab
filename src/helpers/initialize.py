import json
import os
import io
import time
from contextlib import redirect_stderr
from dotenv import load_dotenv
from models.data import Data
from models.market import Path
from helpers.utility import get_healthy_loops_report, get_healthy_triangles_report
from helpers.paths import (
    generate_healthy_path_names,
    load_healthy_loops,
    generate_healthy_loop_names,
    generate_healthy_pairs,
    generate_healthy_triangle_names,
    load_healthy_triangles
)
from brownie import Contract, network, web3

dummy_stderr = io.StringIO()
with redirect_stderr(dummy_stderr):
    from dank_mids.brownie_patch import patch_contract
    from dank_mids import setup_dank_w3_from_sync


def connect(network_name: str) -> None:
    """
    Connects to the network specified by network_name.
    """
    load_dotenv()
    if not network.is_connected():
        network.connect(network_name)


def load_main_contracts() -> tuple[dict[str, Contract],
                                   dict[str, Contract]]:
    """
    Loads contracts via the local abis.
    """
    script_dir = os.path.dirname(os.path.abspath(__file__))
    abi_folder = os.path.join(script_dir, 'assets', 'abi')

    router_abi = json.load(open(os.path.join(abi_folder, "router.json")))
    quoter_abi = json.load(open(os.path.join(abi_folder, "quoter.json")))
    factory_abi = json.load(open(os.path.join(abi_folder, "factory.json")))

    routers = {
        dex_name: Contract.from_abi(
            dex_name, Data.get_router_address_from_name(dex_name), router_abi)
        for dex_name in Data.get_v2_dex_names()
    }

    quoters = {
        dex_name: Contract.from_abi(
            dex_name, Data.get_quoter_address_from_name(dex_name), quoter_abi)
        for dex_name in Data.get_v3_dex_names()
    }

    factories = {
        "F" + dex_name: Contract.from_abi(
            dex_name, Data.get_factory_address_from_name(dex_name), factory_abi)
        for dex_name in Data.get_v2_dex_names()
    }

    return factories, {**routers, **quoters}


def load_pair_contracts() -> dict[str, Contract]:
    """
    Loads pair contracts via the local abis.
    """
    script_dir = os.path.dirname(os.path.abspath(__file__))
    abi_folder = os.path.join(script_dir, 'assets', 'abi')
    pairs_file = os.path.join(script_dir, 'assets', 'healthy_pairs.json')

    pair_abi = json.load(open(os.path.join(abi_folder, "pair.json")))
    pair_addresses = json.load(open(pairs_file))

    pairs = {
        str(path): Contract.from_abi(
            str(path),
            pair_addresses[str(path)],
            pair_abi)
        for path in Path.get_all_v2_paths()
    }

    return pairs


async def setup(network_name: str = "mainnet",
                reload_healthy: bool = False) -> None:
    """
    Main initialization function. Reloads or generates 'healthy_loops' file
    if necessary. 
    """
    start_time = time.perf_counter()
    connect(network_name)
    after_connect_time = time.perf_counter()
    print('Connection took {} seconds'.format(after_connect_time - start_time))

    script_dir = os.path.dirname(os.path.abspath(__file__))
    address_data_file = os.path.join(script_dir, 'assets', 'address_data.json')
    paths_file = os.path.join(script_dir, 'assets', 'healthy_paths')
    pairs_file = os.path.join(script_dir, 'assets', 'healthy_pairs.json')
    triangles_file = os.path.join(
        script_dir, 'assets', 'healthy_triangles.json')

    with open(address_data_file, 'r') as file:
        Data.address_data = json.load(file)

    Data.factories, Data.pricing_contracts = load_main_contracts()

    dank_w3 = setup_dank_w3_from_sync(web3)
    _ = [patch_contract(contract, dank_w3)
         for contract in {**Data.factories,
                          **Data.pricing_contracts}.values()]

    healthy_paths_exists = os.path.exists(paths_file)
    healthy_pairs_exists = os.path.exists(pairs_file)
    healthy_triangles_exists = os.path.exists(triangles_file)

    if reload_healthy or not healthy_paths_exists:
        await generate_healthy_path_names()
        generate_healthy_loop_names()
    Data.lines = load_healthy_loops()

    if reload_healthy or not healthy_pairs_exists:
        await generate_healthy_pairs()
    Data.pairs = load_pair_contracts()

    _ = [patch_contract(pair_contract, dank_w3)
         for pair_contract in Data.pairs.values()]

    if reload_healthy or not healthy_triangles_exists:
        generate_healthy_triangle_names()
    Data.triangles = load_healthy_triangles()

    print(get_healthy_loops_report())
    print(get_healthy_triangles_report())
    end_time = time.perf_counter()
    print('Rest of the setup took {} seconds'.format(
        end_time - after_connect_time))
