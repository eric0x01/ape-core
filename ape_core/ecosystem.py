from typing import Dict, Optional, Type, cast

from ape.api import TransactionAPI
from ape.api.config import PluginConfig
from ape.api.networks import LOCAL_NETWORK_NAME
from ape.types import TransactionSignature
from ape.utils import DEFAULT_LOCAL_TRANSACTION_ACCEPTANCE_TIMEOUT
from ape_ethereum.ecosystem import Ethereum, ForkedNetworkConfig, NetworkConfig
from ape_ethereum.transactions import DynamicFeeTransaction, StaticFeeTransaction, TransactionType

NETWORKS = {
    # chain_id, network_id
    "mainnet": (1116, 1116),
    "testnet": (1115, 1115),
    "devnet": (1112, 1112),
}


def _create_config(
    required_confirmations: int = 1, block_time: int = 3, cls: Type = NetworkConfig, **kwargs
) -> NetworkConfig:
    return cls(
        block_time=block_time,
        default_transaction_type=TransactionType.STATIC,
        required_confirmations=required_confirmations,
        **kwargs,
    )


def _create_local_config(default_provider: Optional[str] = None, use_fork: bool = False, **kwargs):
    return _create_config(
        block_time=0,
        default_provider=default_provider,
        gas_limit="max",
        required_confirmations=0,
        transaction_acceptance_timeout=DEFAULT_LOCAL_TRANSACTION_ACCEPTANCE_TIMEOUT,
        cls=ForkedNetworkConfig if use_fork else NetworkConfig,
        **kwargs,
    )


class COREConfig(PluginConfig):
    mainnet: NetworkConfig = _create_config()
    mainnet_fork: ForkedNetworkConfig = _create_local_config(use_fork=True)
    testnet: NetworkConfig = _create_config()
    testnet_fork: ForkedNetworkConfig = _create_local_config(use_fork=True)
    devnet: NetworkConfig = _create_config()
    devnet_fork: ForkedNetworkConfig = _create_local_config(use_fork=True)
    local: NetworkConfig = _create_local_config(default_provider="test")
    default_network: str = LOCAL_NETWORK_NAME


class CORE(Ethereum):
    @property
    def config(self) -> COREConfig:  # type: ignore[override]
        return cast(COREConfig, self.config_manager.get_config("core"))

    def create_transaction(self, **kwargs) -> TransactionAPI:
        """
        Returns a transaction using the given constructor kwargs.
        Overridden because does not support

        **kwargs: Kwargs for the transaction class.

        Returns:
            :class:`~ape.api.transactions.TransactionAPI`
        """

        transaction_types: Dict[int, Type[TransactionAPI]] = {
            TransactionType.STATIC.value: StaticFeeTransaction,
            TransactionType.DYNAMIC.value: DynamicFeeTransaction,
        }

        if "type" in kwargs:
            if kwargs["type"] is None:
                # The Default is pre-EIP-1559.
                version = self.default_transaction_type.value
            elif not isinstance(kwargs["type"], int):
                version = self.conversion_manager.convert(kwargs["type"], int)
            else:
                version = kwargs["type"]

        elif "gas_price" in kwargs:
            version = TransactionType.STATIC.value
        else:
            version = self.default_transaction_type.value

        kwargs["type"] = version
        txn_class = transaction_types[version]

        if "required_confirmations" not in kwargs or kwargs["required_confirmations"] is None:
            # Attempt to use default required-confirmations from `ape-config.yaml`.
            required_confirmations = 0
            active_provider = self.network_manager.active_provider
            if active_provider:
                required_confirmations = active_provider.network.required_confirmations

            kwargs["required_confirmations"] = required_confirmations

        if isinstance(kwargs.get("chainId"), str):
            kwargs["chainId"] = int(kwargs["chainId"], 16)

        elif "chainId" not in kwargs and self.network_manager.active_provider is not None:
            kwargs["chainId"] = self.provider.chain_id

        if "input" in kwargs:
            kwargs["data"] = kwargs.pop("input")

        if all(field in kwargs for field in ("v", "r", "s")):
            kwargs["signature"] = TransactionSignature(
                v=kwargs["v"],
                r=bytes(kwargs["r"]),
                s=bytes(kwargs["s"]),
            )

        if "max_priority_fee_per_gas" in kwargs:
            kwargs["max_priority_fee"] = kwargs.pop("max_priority_fee_per_gas")
        if "max_fee_per_gas" in kwargs:
            kwargs["max_fee"] = kwargs.pop("max_fee_per_gas")

        kwargs["gas"] = kwargs.pop("gas_limit", kwargs.get("gas"))

        if "value" in kwargs and not isinstance(kwargs["value"], int):
            kwargs["value"] = self.conversion_manager.convert(kwargs["value"], int)

        return txn_class(**kwargs)
