import random
import json

import numpy as np

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


def node_config_to_string(nodes):
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
        yield nodes

_generators['uniform'] = generate_uniform


def generate_trophic_level_scaling(node_ids, param_ranges, factor, count):
    """ Like generate_uniform, but reduce initialBiomass according to
    trophic level.

    initialBiomass is multiplied by factor ** max_food_chain_length
    (food chain length is the number of links).

    Parameters
    ----------
    node_ids : list
        Node IDs of nodes to include in the generated node configs
    param_ranges : dict
        Ranges of values to use for each parameter.
        Key: parameter name
        Value: [low, high] (or a single fixed value)
    factor : float
        Factor by which to multiply initial biomass for each increase in
        trophic level
    count
        Number of node configs to generate

    Yields
    -------
    str
        Node config string
    """
    subweb = foodwebs.get_serengeti().subgraph(node_ids)

    max_chain_length = {node_id: 0 for node_id in node_ids}  # maximum food chain length by species
    food_chains = foodwebs.get_food_chains(subweb)
    food_chains.sort(key=lambda c: list(reversed(c)))
    for chain in food_chains:
        print(str(chain))

    for chain in food_chains:
        node_id = chain[-1]
        max_chain_length[node_id] = max(max_chain_length[node_id], len(chain) - 1)  # subtract 1 to count edges

    for node_config in generate_uniform(node_ids, param_ranges, count):
        for node in node_config:
            node['initialBiomass'] *= factor ** (max_chain_length[node['nodeId']])
        yield node_config

_generators['trophic-level-scaling'] = generate_trophic_level_scaling


def generate_parallel_sweep(node_ids, param_ranges, count):
    """
    Generate `count` node configs for the given node ID's with parameter
    values evenly spaced across the given ranges for successive node
    configs. All parameter values change in parallel.

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

    # Compute sequence of values for each parameter
    param_values = {}
    for param, range_ in param_ranges.items():
        # Handle fixed parameter values (convert single values into lists with the same value for low and high)
        if not isinstance(range_, list):
            range_ = [range_, range_]
        param_values[param] = np.linspace(*range_, num=count, endpoint=True, dtype=np.float64)

    for i in range(count):
        nodes = []
        for node_id in node_ids:
            node = {
                'nodeId': node_id,
                'initialBiomass': param_values['initialBiomass'][i],
                'perUnitBiomass': serengeti.node[node_id]['biomass']
            }
            if serengeti.node[node_id]['organism_type'] == foodwebs.ORGANISM_TYPE_ANIMAL:
                node['X'] = param_values['X'][i]
            else:
                node['K'] = param_values['K'][i]
                if 'R' in param_ranges:
                    node['R'] = param_values['R'][i]
            nodes.append(node)
        yield nodes

_generators['parallel_sweep'] = generate_parallel_sweep


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

    return (node_config_to_string(nc) for nc in generator_function(**kwargs))
