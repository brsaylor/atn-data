import random
import json

from atntools import foodwebs

# Parameter sliders in Convergence game are bounded by these ranges
valid_param_ranges = {
    'K': (1000, 15000),
    'R': (0, 3),
    'X': (0, 1),

    # Initial biomass is not varied in Convergence, but we still need upper and
    # lower bounds for other purposes
    'initialBiomass': (0, 15000)
}

# node_config syntax is as follows (no carriage returns):
#
# 1. #, //#=number of nodes
# 2. [#], //[#]=next node ID (species)
# 3. #, //#=total biomass
# 4. #, //#=per-unit-biomass
# 5. #, //#=number of node parameters configured (exclude next line if = 0)
# 6. p=#, //p=node parameter ID (K, R, X) for (carrying capacity, growth rate,
#           met-rate)
#  {repeat 6 based on number given in 5}
# 7. #, //#=number of link parameters configured (exclude next two lines if = 0)
# 8. [#], //[#]=link node ID (linked species)
# 9. p=#, //p=link parameter ID (A, E, D, Q, Y)
#  {repeat 8-9 based on number given in 7}
#  {repeat 2-9 based on number given in 1}
# 


def parse_node_config(node_config):
    """
    Parse a node config string and return a list-of-dicts representation.
    """
    nodes = []
    config_list = node_config.split(',')
    num_nodes = int(config_list[0])

    pos = 1  # current position in the comma-split list

    for i in range(num_nodes):
        node = {
                'nodeId': int(config_list[pos][1:-1]),  # FIXME validate [#]
                'initialBiomass': float(config_list[pos+1]),
                'perUnitBiomass': float(config_list[pos+2]),
                }
        num_params = int(config_list[pos+3])
        pos += 4
        for p in range(num_params):
            param_name, param_value = config_list[pos].split('=')
            node[param_name] = float(param_value)
            pos += 1
        pos += 1  # FIXME assuming there are no node link parameters
        nodes.append(node)

    return nodes


def generate_node_config(nodes):
    """
    Convert a list-of-dicts representation of a node config into a string.
    """

    node_config = str(len(nodes))
    for node in nodes:
        node_config += (',[{nodeId}],{initialBiomass:.6},{perUnitBiomass},'
                        .format(**node))

        param_count = 0
        param_config = ''
        for param in ('K', 'R', 'X'):
            if param in node:
                param_config += '{}={:.6},'.format(param, float(node[param]))
                param_count += 1

        # The final 0 is for the number of link parameters, which is always 0
        node_config += '{},{}0'.format(param_count, param_config)

    return node_config

# FIXME: Move the test into a test module
#
# Change from Convergence 5-species template: addition of R for the grass.
# Inspection of WoB_Server code (SimJob) reveals that R defaults to 1.0.
# test_node_config = '5,[5],2000.0,1.0,2,K=10000.0,R=1.0,0,[14],1751.0,20.0,1,X=0.201,0,[31],1415.0,0.0075,1,X=1.0,0,[42],240.0,0.205,1,X=0.637,0,[70],2494.0,13.0,1,X=0.155,0'
#
# test_nodes = [
#     {
#         'nodeId': 5,
#         'initialBiomass': 2000.0,
#         'perUnitBiomass': 1.0,
#         'K': 10000.0,
#         'R': 1.0,
#     },
#     {
#         'nodeId': 14,
#         'initialBiomass': 1751.0,
#         'perUnitBiomass': 20.0,
#         'X': 0.201,
#     },
#     {
#         'nodeId': 31,
#         'initialBiomass': 1415.0,
#         'perUnitBiomass': 0.0075,
#         'X': 1.0,
#     },
#     {
#         'nodeId': 42,
#         'initialBiomass': 240.0,
#         'perUnitBiomass': 0.205,
#         'X': 0.637,
#     },
#     {
#         'nodeId': 70,
#         'initialBiomass': 2494.0,
#         'perUnitBiomass': 13.0,
#         'X': 0.155,
#     },
# ]
#
# # Verify that parseNodeConfig and generateNodeConfig work correctly
# assert(parse_node_config(test_node_config) == test_nodes)
# assert(generate_node_config(test_nodes) == test_node_config)


_generators = {}


def generate_uniform(node_ids, param_ranges, count):
    """
    Generate `count` node configs for the given node ID's with parameter
    values independently drawn from uniform random distributions with the
    given ranges.

    Parameters
    ----------
    node_ids : list
        Node IDs of nodes to include in the generated node configs
    param_ranges : dict
        Ranges of values to use for each parameter.
        Key: parameter name
        Value: [low, high] (or a single fixed value)
    count
        Number of node configs to generate

    Yields
    -------
    str
        Node config string
    """

    serengeti = foodwebs.get_serengeti()

    # Handle fixed parameter values (convert single values into lists with the same value for low and high)
    for k, v in param_ranges.items():
        if not isinstance(v, list):
            param_ranges[k] = [v, v]

    for i in range(count):
        nodes = []
        for node_id in node_ids:
            node = {
                'nodeId': node_id,
                'initialBiomass': random.uniform(*param_ranges['initialBiomass']),
                'perUnitBiomass': serengeti.node[node_id]['biomass']
            }
            if serengeti.node[node_id]['organism_type'] == foodwebs.ORGANISM_TYPE_ANIMAL:
                node['X'] = random.uniform(*param_ranges['X'])
            else:
                node['K'] = random.uniform(*param_ranges['K'])
                if 'R' in param_ranges:
                    node['R'] = random.uniform(*param_ranges['R'])
            nodes.append(node)
        yield generate_node_config(nodes)

_generators['uniform'] = generate_uniform


def generate_node_configs_from_metaparameter_file(metaparameter_filename, food_web_filename=None):
    """
    Generate node config strings based on the given metaparameter JSON file.

    Parameters
    ----------
    metaparameter_filename : str
        Path to JSON metaparameter file
    food_web_filename : str, optional
        If supplied, the node IDs are taken from this file instead of the
        metaparameter file.

    Returns
    -------
    generator
        A generator that yields node config strings
    """

    global _generators

    with open(metaparameter_filename) as f:
        metaparameters = json.load(f)
    generator_name = metaparameters.get('generator')
    if generator_name in _generators:
        generator_function = _generators[generator_name]
    else:
        return None
    kwargs = metaparameters.get('args')
    if not isinstance(kwargs, dict):
        return None

    if food_web_filename is not None:
        with open(food_web_filename) as f:
            food_web_data = json.load(f)
            kwargs.update(food_web_data)

    return generator_function(**kwargs)
