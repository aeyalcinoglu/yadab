import json
import requests
import os
from collections import Counter, defaultdict
from models.data import Data
from brownie import Contract, network, project, accounts


def get_remaning_paths(middle_paths, line_paths):
    new_paths = []
    for line_path in line_paths:
        if line_path not in middle_paths:
            new_paths.append(line_path)
    return new_paths, len(middle_paths), len(new_paths) + len(middle_paths)


def fill_missing_triangles(messy_triangles):
    all_messy_triangles = []
    for middle_path in messy_triangles.keys():
        for left_path in messy_triangles[middle_path].keys():
            for right_path in messy_triangles[middle_path][left_path]:
                all_messy_triangles.append(
                    (left_path, middle_path, right_path))

    candidate_triangles = []
    for messy_triangle in all_messy_triangles:
        l, m, r = messy_triangle
        for candidate_triangle in [(l, m, r), (r, l, m), (m, r, l)]:
            candidate_triangles.append(candidate_triangle)

    seen = set()
    cleaned_triangles = [x for x in candidate_triangles
                         if not (x in seen or seen.add(x))]

    dict_of_triangles = defaultdict(lambda: defaultdict(list))
    for l, m, r in cleaned_triangles:
        dict_of_triangles[m][l].append(r)
    return dict_of_triangles


def get_healthy_loops_report() -> str:
    """
    Returns a report on the architecture of the healthy loops.
    """
    distribution = defaultdict(int)

    for forward_path, backward_paths in Data.lines.items():
        for backward_path in backward_paths:
            if forward_path.dex.name.endswith('v2'):
                if backward_path.dex.name.endswith('v2'):
                    distribution["v22"] += 1
                if backward_path.dex.name.endswith('v3'):
                    distribution["v23"] += 1
            if forward_path.dex.name.endswith('v3'):
                if backward_path.dex.name.endswith('v2'):
                    distribution["v32"] += 1
                if backward_path.dex.name.endswith('v3'):
                    distribution["v33"] += 1

    report_string = "Total 2-cycles: {}, v22: {}, v23: {}, v32: {}, v33: {}".format(sum(distribution.values()),
                                                                                    distribution["v22"],
                                                                                    distribution["v23"],
                                                                                    distribution["v32"],
                                                                                    distribution["v33"])

    return report_string


def get_healthy_triangles_report() -> str:
    counts = {
        "v222": 0,
        "v223": 0,
        "v233": 0,
        "v333": 0
    }

    real_triangles = []
    for middle_path in list(Data.triangles.keys()):
        left_paths = list(Data.triangles[middle_path].keys())
        for left_path in left_paths:
            for right_path in Data.triangles[middle_path][left_path]:
                real_triangles.append((left_path, middle_path, right_path))

    for triangle in real_triangles:
        versions = [str(item).split()[0][-1:] for item in triangle]
        version_counter = Counter(versions)

        if version_counter == Counter({'2': 3}):
            counts["v222"] += 1
        elif version_counter == Counter({'2': 2, '3': 1}):
            counts["v223"] += 1
        elif version_counter == Counter({'2': 1, '3': 2}):
            counts["v233"] += 1
        elif version_counter == Counter({'3': 3}):
            counts["v333"] += 1

    total_count = sum(counts.values())
    formatted_string = (
        "Total 3-cycles: {}, "
        "{}: {}, "
        "{}: {}, "
        "{}: {}, "
        "{}: {}"
    ).format(total_count, "v222", counts['v222'], "v223", counts['v223'], "v233", counts['v233'], "v333", counts['v333'])

    return formatted_string


def send_notification(message: str) -> None:
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    if token:
        for chat_id in [os.environ.get("FIRST_TELEGRAM_CHAT_ID"),
                        os.environ.get("SECOND_TELEGRAM_CHAT_ID")]:

            url = "https://api.telegram.org/bot{}/sendMessage?chat_id={}&text={}".format(
                token, chat_id, message)
            requests.get(url)


def get_abi_from_cache(name: str, address: str) -> dict:
    """
    Gets the abi from the cache if it exists, otherwise it gets it from the
    blockchain via Etherscan and saves it to the "abi" folder.
    """
    script_dir = os.path.dirname(os.path.abspath(__file__))
    abi_folder = os.path.join(script_dir, 'assets', 'abi')
    abi_file_path = os.path.join(abi_folder, "{}.json".format(name))

    try:
        with open(abi_file_path, "r") as file:
            abi = json.load(file)
            return abi
    except FileNotFoundError:
        pass

    abi = Contract.from_explorer(address).abi
    os.makedirs(abi_folder, exist_ok=True)

    with open(abi_file_path, "w") as file:
        json.dump(abi, file)

    return abi


def deploy_contract(contract_name: str, account_name: str) -> str:
    """
    Deploys a contract.
    Only works on contracts without constructor arguments.
    """
    network_name = network.show_active()
    account = accounts.load(account_name)
    contract = project.load("./")[contract_name]
    estimated_gas = contract.deploy.estimate_gas(1, {"from": account})
    print(
        f"Deploying to {network_name} network, estimated gas: {estimated_gas}")
    return contract.deploy(1, {"from": account},
                           publish_source=(network_name != "development")).address
