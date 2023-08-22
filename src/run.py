import asyncio
import logging
import time
import os
import heapq
from collections import defaultdict
from brownie import web3
from models.data import Data
from models.market import Path
from helpers.initialize import setup
from helpers.utility import send_notification
from helpers.arbitrage import calculate_arbitrage
from helpers.price import update_v2_reserves


async def _main(critical_arb):
    block_number = web3.eth.get_block_number()
    logging.info("\nBlock: {}".format(block_number))
    line_logs = []
    triangular_logs = []
    positive_triangles = Data.triangles
    positive_lines = Data.lines
    all_triangular_positive = []
    all_line_positive = []
    len_check = 0
    await update_v2_reserves()
    for amount_in in base_amount_ins:
        line_arbitrage_results, triangular_arbitrage_results = (await asyncio.gather(
            *[calculate_arbitrage(positive_lines, positive_triangles,
                                  amount_in)]))[0]
        positive_triangles = defaultdict(lambda: defaultdict(list))
        positive_lines = defaultdict(list)
        for line_arbitrage_result in line_arbitrage_results:
            forward_path, backward_path, arb = line_arbitrage_result
            if arb > minArb:
                line_string = Path.get_line_string(forward_path,
                                                   backward_path)
                all_line_positive.append(
                    (amount_in, line_string, arb))
                positive_lines[forward_path].append(backward_path)
        if not len_check:
            print("There are {} line arbitrages".format(
                len(all_line_positive)))
            len_check += 1
        for triangular_arbitrage_result in triangular_arbitrage_results:
            left_path, middle_path, right_path, arb = triangular_arbitrage_result
            if arb > minArb:
                all_triangular_positive.append(
                    (amount_in, left_path, middle_path, right_path, arb))
                positive_triangles[middle_path][left_path].append(right_path)
        if len_check < 2:
            print("There are {} triangular arbitrages".format(
                len(all_triangular_positive)))
            len_check += 1
    try:
        top_two_pair = heapq.nlargest(2, all_line_positive, key=lambda t: t[2])
        for amount, line_string, arb in top_two_pair:
            line_logs.append("{} {} {}".format(
                amount, line_string, round(arb, 4)))
    except:
        logging.info("No line arbitrage or broken!")
    try:
        top_two_pair = heapq.nlargest(
            2, all_triangular_positive, key=lambda t: t[4])
        for amount_in, left_path, middle_path, right_path, arb in top_two_pair:
            triangular_logs.append("{} {} {}".format(
                amount_in, Path.get_triangle_string(left_path,
                                                    middle_path,
                                                    right_path), round(arb, 4)))
    except:
        logging.info("No triangular arbitrage or broken!")

    logs = line_logs + triangular_logs
    hit = False
    for log in logs:
        if float(log.split(' ')[-1]) > critical_arb:
            hit = True
            send_notification(str(block_number) + " " + log)
        logging.info(log)
    return int(hit)


async def main():
    critical_arb = 5
    total_messages = 0
    await setup()
    while True:
        start_time = time.perf_counter()
        total_messages += await _main(critical_arb + total_messages)
        end_time = time.perf_counter()
        print('Time: {} seconds'.format(end_time - start_time))


if __name__ == "__main__":
    script_dir = os.path.dirname(os.path.abspath(__file__))
    log_file_name = 'optimized_arbitrage_results.log'
    logging.basicConfig(filename=os.path.join(script_dir, log_file_name),
                        format='%(message)s', encoding='utf-8', level=logging.INFO)
    logging.getLogger().addHandler(logging.StreamHandler())
    base_amount_ins = [30, 61, 98, 134, 214, 600, 1700, 4444, 10000, 100000]
    minArb = 0.001
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())
