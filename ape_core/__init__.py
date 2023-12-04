from ape import plugins
from ape.api.networks import LOCAL_NETWORK_NAME, ForkedNetworkAPI, NetworkAPI, create_network_type
from ape_geth import GethProvider
from ape_test import LocalProvider

from .ecosystem import CORE, NETWORKS, COREConfig


@plugins.register(plugins.Config)
def config_class():
    return COREConfig


@plugins.register(plugins.EcosystemPlugin)
def ecosystems():
    yield CORE


@plugins.register(plugins.NetworkPlugin)
def networks():
    for network_name, network_params in NETWORKS.items():
        yield "core", network_name, create_network_type(*network_params)
        yield "core", f"{network_name}-fork", ForkedNetworkAPI

    # NOTE: This works for development providers, as they get chain_id from themselves
    yield "core", LOCAL_NETWORK_NAME, NetworkAPI


@plugins.register(plugins.ProviderPlugin)
def providers():
    for network_name in NETWORKS:
        yield "core", network_name, GethProvider

    yield "core", LOCAL_NETWORK_NAME, LocalProvider
