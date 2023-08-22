from dataclasses import dataclass
from models.data import Data
from functools import lru_cache
from brownie import Contract
import os


@dataclass(frozen=True)
class Dex:
    name: str
    pricing_contract: Contract
    factory: Contract = None
    fee: int = 3000

    @staticmethod
    @lru_cache(maxsize=None)
    def get_dex_from_name(dex_name: str) -> "Dex":
        if dex_name.endswith('v2'):
            return Dex(dex_name,
                       Data.pricing_contracts[dex_name],
                       Data.factories["F" + dex_name])
        return Dex(dex_name,
                   Data.pricing_contracts[dex_name])

    def __str__(self) -> str:
        return self.name


class Token:
    def __init__(self, name: str,
                 address: str,
                 relative_price: int,
                 decimals: int) -> None:
        self.name = name
        self.relative_price = relative_price
        self.address = address
        self.decimals = decimals

    @staticmethod
    @lru_cache(maxsize=None)
    def get_token_from_name(token_name: str) -> "Token":
        return Token(token_name,
                     Data.get_token_address_from_name(token_name),
                     Data.get_token_relative_price_from_name(token_name),
                     Data.get_token_decimals_from_name(token_name))

    def get_relative_price(self, amount_in: float) -> float:
        """
        Converts USD amount to token amount.
        """
        return amount_in * \
            self.relative_price * \
            10**self.decimals

    def recover_original_price(self, amount_in: float) -> float:
        """
        Converts token amount to USD amount.
        """
        return amount_in / (self.relative_price *
                            10**self.decimals)

    def __str__(self) -> str:
        return self.name


@dataclass(frozen=True)
class Path:
    dex: Dex
    from_token: Token
    to_token: Token

    @staticmethod
    @lru_cache(maxsize=None)
    def get_path_from_name(dex_name: str,
                           from_token_name: str,
                           to_token_name: str) -> "Path":
        return Path(Dex.get_dex_from_name(dex_name),
                    Token.get_token_from_name(from_token_name),
                    Token.get_token_from_name(to_token_name))

    @staticmethod
    def is_composable(start_path: "Path", return_path: "Path") -> bool:
        return start_path.to_token == return_path.from_token

    def get_token_path(self) -> list[Token]:
        return [self.from_token, self.to_token]

    def get_address_path(self) -> list[str]:
        return [self.from_token.address, self.to_token.address]

    @staticmethod
    def get_line_string(forward_path: "Path", backward_path: "Path") -> str:
        return "{} {} {} {}".format(forward_path.dex.name,
                                    backward_path.dex.name,
                                    forward_path.from_token.name,
                                    backward_path.from_token.name)

    @staticmethod
    def get_triangle_string(left_path: "Path",
                            middle_path: "Path",
                            right_path: "Path") -> str:
        return "{} {} {} {} {} {}".format(left_path.dex.name,
                                          middle_path.dex.name,
                                          right_path.dex.name,
                                          left_path.from_token.name,
                                          middle_path.from_token.name,
                                          right_path.from_token.name)

    @staticmethod
    @lru_cache(maxsize=None)
    def get_all_v2_paths() -> list["Path"]:
        all_v2_paths = []  # return unique list

        script_dir = os.path.dirname(os.path.abspath(__file__))
        parent_dir = os.path.dirname(script_dir)
        paths_file = os.path.join(
            parent_dir, 'helpers', 'assets', 'healthy_paths')

        with open(paths_file, 'r') as file:
            unique_v2_path_names = list(
                set([path_name.strip()
                     for path_name in file.readlines()
                     if path_name.strip().split(' ')[0].endswith('v2')]))

        return [Path.get_path_from_name(*path_name.split(' ')) for path_name in unique_v2_path_names]

    def __str__(self) -> str:
        return "{} {} {}".format(self.dex,
                                 self.from_token,
                                 self.to_token)
