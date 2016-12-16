import random

from atntools.nodeconfigs import *

# Change from Convergence 5-species template: addition of R for the grass.
# Inspection of WoB_Server code (SimJob) reveals that R defaults to 1.0.
test_node_config = '5,[5],2000.0,1.0,2,K=10000.0,R=1.0,0,[14],1751.0,20.0,1,X=0.201,0,[31],1415.0,0.0075,1,X=1.0,0,[42],240.0,0.205,1,X=0.637,0,[70],2494.0,13.0,1,X=0.155,0'

test_nodes = [
    {
        'nodeId': 5,
        'initialBiomass': 2000.0,
        'perUnitBiomass': 1.0,
        'K': 10000.0,
        'R': 1.0,
    },
    {
        'nodeId': 14,
        'initialBiomass': 1751.0,
        'perUnitBiomass': 20.0,
        'X': 0.201,
    },
    {
        'nodeId': 31,
        'initialBiomass': 1415.0,
        'perUnitBiomass': 0.0075,
        'X': 1.0,
    },
    {
        'nodeId': 42,
        'initialBiomass': 240.0,
        'perUnitBiomass': 0.205,
        'X': 0.637,
    },
    {
        'nodeId': 70,
        'initialBiomass': 2494.0,
        'perUnitBiomass': 13.0,
        'X': 0.155,
    },
]


def test_parse_node_config():
    assert parse_node_config(test_node_config) == test_nodes


def test_node_config_to_string():
    assert node_config_to_string(test_nodes) == test_node_config


def test_generate_trophic_level_scaling(monkeypatch):

    # Make random.uniform() just return the high value
    monkeypatch.setattr(random, 'uniform', lambda low, high: high)

    args = {
        "node_ids": [3, 4, 5, 7, 13, 30, 31, 42, 45, 49, 50, 51, 52, 53, 57, 65, 72, 74, 75, 85],
        "param_ranges": {
            "initialBiomass": [100, 8000],
            "X": [0, 1],
            "R": 1,
            "K": [100, 10000]
        },
        "factor": 0.25,
        "count": 1
    }

    node_configs = list(generate_trophic_level_scaling(**args))

    assert len(node_configs) == 1
    node_config = node_configs[0]

    max_chain_lengths = {13: 1, 30: 1, 31: 1, 42: 2, 45: 2, 49: 3, 50: 2, 51: 3, 52: 1, 53: 3, 57: 3, 65: 1, 72: 1, 74: 2, 75: 2, 85: 1}
    for node in node_config:
        assert node['initialBiomass'] == 8000 * 0.25 ** max_chain_lengths.get(node['nodeId'], 0)
