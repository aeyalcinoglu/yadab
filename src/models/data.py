class Data:
    address_data = None
    pricing_contracts = None
    factories = None
    lines = None
    pairs = None
    reserves = None
    triangles = None

    @staticmethod
    def get_token_address_from_name(token_name: str) -> str:
        return Data.address_data['token'][token_name]['address']

    @staticmethod
    def get_token_decimals_from_name(token_name: str) -> int:
        return Data.address_data['token'][token_name]['decimals']

    @staticmethod
    def get_token_relative_price_from_name(token_name: str) -> int:
        return Data.address_data['token'][token_name]['relative_price']

    @staticmethod
    def get_router_address_from_name(dex_name: str) -> str:
        return Data.address_data['dex'][dex_name]['router_address']

    @staticmethod
    def get_quoter_address_from_name(quoter_name: str) -> str:
        return Data.address_data['dex'][quoter_name]['quoter_address']

    @staticmethod
    def get_factory_address_from_name(dex_name: str) -> str:
        return Data.address_data['dex'][dex_name]['factory_address']

    @staticmethod
    def get_dex_names() -> list[str]:
        return list(Data.address_data['dex'].keys())

    @staticmethod
    def get_v2_dex_names() -> list[str]:
        return [dex_name for dex_name in Data.address_data['dex'].keys()
                if dex_name.endswith('v2')]

    @staticmethod
    def get_v3_dex_names() -> list[str]:
        return [dex_name for dex_name in Data.address_data['dex'].keys()
                if dex_name.endswith('v3')]

    @staticmethod
    def get_token_names() -> list[str]:
        return list(Data.address_data['token'].keys())
