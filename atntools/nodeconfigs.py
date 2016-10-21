#!/usr/bin/env python3

# Ben Saylor
# October 2015

import sys
from copy import copy, deepcopy
import random
import re
import itertools
import bisect

from atntools import util
from atntools.weka_em import parse_weka_em_output

# Functions that generate and print out node configs, keyed by set number.
generator_functions = {}

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

# 5-species template from Convergence game:
#
# 5,[5],2000.0,1.0,1,K=10000.000,0,[14],1751.0,20.0,1,X=0.201,0,[31],1415.0,0.0075,1,X=1.000,0,[42],240.0,0.205,1,X=0.637,0,[70],2494.0,13.0,1,X=0.155,0
#
#  5    Grass and Herbs
# 14    Crickets
# 31    Tree Mouse
# 42    African Grey Hornbill
# 70    African Clawless Otter

# All nodeconfigs for target ecosystems from Convergence game
convergence_node_configs = [
    '5,[5],2000.0,1.0,1,K=10000.000,0,[14],1751.0,20.0,1,X=0.201,0,[31],1415.0,0.0075,1,X=1.000,0,[42],240.0,0.205,1,X=0.637,0,[70],2494.0,13.0,1,X=0.155,0',

    '6,[5],2000,1.000,1,K=8000.000,0,[14],1051,20.000,1,X=0.200,0,[31],29,0.008,1,X=0.950,0,[33],2476,0.400,1,X=0.370,0,[56],738,6.250,1,X=0.180,0,[59],674,3.350,1,X=0.220,0',

    '11,[2],433,528.000,2,R=2.000,K=3000.000,0,[3],433,528.000,1,K=3000.000,0,[4],433,528.000,1,K=3000.000,0,[5],2000,1.000,1,K=4000.000,0,[7],668,816.000,1,K=3000.000,0,[49],1308,0.355,1,X=0.870,0,[55],576,0.213,1,X=0.990,0,[61],601,54.000,1,X=0.010,0,[74],725,50.000,1,X=0.100,0,[82],700,50.000,1,X=0.750,0,[83],300,103.000,1,X=0.210,0',

    '15,[1],400,1.000,1,K=2000.000,0,[2],1056,20.000,1,K=3000.000,0,[5],2000,1.000,1,K=7000.000,0,[7],1322,40.000,1,K=3000.000,0,[9],1913,0.071,1,X=0.310,0,[12],300,1.000,0,0,[26],1164,0.011,1,X=1.000,0,[45],916,0.425,1,X=0.400,0,[49],1015,0.355,1,X=0.300,0,[55],1849,0.310,1,X=0.480,0,[67],1434,9.600,1,X=0.340,0,[71],564,4.990,1,X=0.270,0,[75],568,1.590,1,X=0.010,0,[80],575,41.500,1,X=0.220,0,[87],240,112.000,1,X=0.100,0',

    '17,[1],2000,1000.000,2,K=3000.000,X=0.052,0,[2],657,528.000,1,K=3000.000,0,[3],657,528.000,1,K=3000.000,0,[4],657,528.000,1,K=3000.000,0,[5],2000,1.000,1,K=5000.000,0,[7],1015,816.000,1,K=3000.000,0,[19],211,20.000,1,X=0.100,0,[21],400,0.200,1,X=0.200,0,[26],496,0.011,1,X=0.910,0,[29],964,0.035,1,X=0.680,0,[31],700,0.008,1,X=1.000,0,[35],1000,250.000,1,X=0.070,0,[36],1322,3.500,1,X=0.010,0,[39],1178,0.085,1,X=0.540,0,[56],1281,6.250,1,X=0.090,0,[66],203,10.200,1,X=0.160,0,[80],719,41.500,1,X=0.120,0',
    ]

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

# Verify that parseNodeConfig and generateNodeConfig work correctly
assert(parse_node_config(test_node_config) == test_nodes)
assert(generate_node_config(test_nodes) == test_node_config)

def generate_set_1():
    """
    Vary one node at a time, one parameter at a time, based on the 5-species
    ecosystem from the Convergence game. Parameters are varied in a +/- 50%
    range in 5% increments.
    """

    template_nodes = test_nodes
    nodes = deepcopy(template_nodes)

    # Print unaltered nodeconfig first
    print(generate_node_config(nodes))

    # Change one node at a time
    for i in range(len(nodes)):

        # Vary one parameter at a time, +/- 50% in 5% increments
        for param in ('initialBiomass', 'K', 'R', 'X'):
            if param in nodes[i]:
                for percent in range(50, 151, 5):

                    # Don't print the original nodeconfig again
                    if percent == 100:
                        continue

                    nodes[i][param] = test_nodes[i][param] * percent / 100
                    print(generate_node_config(nodes))
                nodes[i] = copy(test_nodes[i])  # reset the node

# FIXME: Print unaltered nodeconfig first, skip in loop
def generatePairVariations(template_nodes, param,
        minPercent, maxPercent, stepPercent, startPos=0):
    """
    For each pair of nodes in 'template_nodes' with parameter 'param', print node
    configs with all combinations of values for 'param' within the given
    percentage range.

    The startPos parameter is the node index at which to start the procedure
    (nodes before this position are not varied).
    """

    nodes = deepcopy(template_nodes)

    for i in range(startPos, len(nodes) - 1):
        if param not in nodes[i]:
            continue
        for j in range(i + 1, len(nodes)):
            if param not in nodes[j]:
                continue

            # Now, two nodes i and j are selected.
            # Generate all combinations of values of 'param' for i and j
            for percent_i in range(minPercent, maxPercent + 1, stepPercent):
                nodes[i][param] = template_nodes[i][param] * percent_i / 100
                for percent_j in range(minPercent, maxPercent + 1, stepPercent):
                    nodes[j][param] = template_nodes[j][param] * percent_j / 100
                    print(generate_node_config(nodes))

            nodes[j] = copy(template_nodes[j])  # reset node j
        nodes[i] = copy(template_nodes[i])  # reset node i

def generateTripleVariations(template_nodes, param,
        minPercent, maxPercent, stepPercent):
    """
    Like generatePairVariations, but with every combination of three nodes that
    have parameter 'param'.
    """

    nodes = deepcopy(template_nodes)

    for k in range(len(nodes) - 2):
        if param not in nodes[k]:
            continue
        for percent in range(minPercent, maxPercent + 1, stepPercent):
            nodes[k][param] = template_nodes[k][param] + percent / 100
            generatePairVariations(nodes, param,
                    minPercent, maxPercent, stepPercent, startPos=k+1)
        nodes[k] = copy(template_nodes[k])  # reset node k

def generate_set_2():
    """
    Base config: testNodes
    For each pair of nodes with an X parameter, generate configs with all
    combinations of X values ranging between +/- 50% of the original value, in
    10% increments.
    """
    generatePairVariations(test_nodes, 'X', 50, 150, 10)

def generate_set_3():
    """
    Base config: testNodes
    """
    generateTripleVariations(test_nodes, 'X', 50, 150, 10)

def generate_set_4():
    """
    Base config: testNodes
    Try various combinations of K and R for the grass, and for each combination,
    vary X of each other node.
    """
    nodes = deepcopy(test_nodes)
    for percentK in range(50, 151, 10):
        nodes[0]['K'] = test_nodes[0]['K'] * percentK / 100
        for percentR in range(50, 151, 10):
            nodes[0]['R'] = test_nodes[0]['R'] * percentR / 100
            for i in range(1, len(nodes)):
                for percentX in range(50, 151, 10):
                    nodes[i]['X'] = test_nodes[i]['X'] * percentX / 100
                    print(generate_node_config(nodes))
                nodes[i] = copy(test_nodes[i])  # reset node i

convergeEcosystem3NodeConfig = '11,[2],433,528.000,2,R=2.000,K=3000.000,0,[3],433,528.000,1,K=3000.000,0,[4],433,528.000,1,K=3000.000,0,[5],2000,1.000,1,K=4000.000,0,[7],668,816.000,1,K=3000.000,0,[49],1308,0.355,1,X=0.870,0,[55],576,0.213,1,X=0.990,0,[61],601,54.000,1,X=0.010,0,[74],725,50.000,1,X=0.100,0,[82],700,50.000,1,X=0.750,0,[83],300,103.000,1,X=0.210,0'

convergeEcosystem3Nodes = parse_node_config(convergeEcosystem3NodeConfig)

def generateAllParamSingleVariations(template_nodes,
        minPercent, maxPercent, stepPercent):
    """
    (Similar to generate_set_1) Vary one node at a time, one parameter at a time,
    based on template_nodes.  Parameters are varied in from minPercent to
    maxPercent in stepPercent increments.
    """

    # Write the unaltered nodeconfig first
    print(generate_node_config(template_nodes))

    nodes = deepcopy(template_nodes)

    # Change one node at a time
    for i in range(len(nodes)):

        # Vary one parameter at a time, +/- 50% in 5% increments
        for param in ('initialBiomass', 'K', 'R', 'X'):
            if param in nodes[i]:
                for percent in range(minPercent, maxPercent + 1, stepPercent):

                    # Don't print the original nodeconfig again
                    if percent == 100:
                        continue

                    nodes[i][param] = template_nodes[i][param] * percent / 100
                    print(generate_node_config(nodes))
                nodes[i] = copy(template_nodes[i])  # reset the node

def generate_random_variations(template_nodes,
                               params, minPercent, maxPercent, count):
    """
    Generate <count> random variations of parameter values on all nodes,
    for parameters named in <params>.
    """
    minRatio = minPercent / 100
    maxRatio = maxPercent / 100
    params = set(params)

    # Write the unaltered nodeconfig first
    print(generate_node_config(template_nodes))

    nodes = deepcopy(template_nodes)
    for i in range(count - 1):
        for j, node in enumerate(nodes):
            for param in node.keys():
                if param in params:
                    node[param] = (template_nodes[j][param] *
                            random.uniform(minRatio, maxRatio))
                    # Limit parameter ranges
                    if param in valid_param_ranges:
                        node[param] = util.clip(node[param],
                                                *valid_param_ranges[param])
        print(generate_node_config(nodes))

def sweepParamForNode(template_nodes, nodeId, param,
        minPercent, maxPercent, count):
    """ Generate <count> nodeconfigs in which the given param for the given node
    is varied from minPercent to maxPercent of the original value. """

    minRatio = minPercent / 100
    maxRatio = maxPercent / 100

    nodes = deepcopy(template_nodes)
    for i in range(count):
        for j, node in enumerate(nodes):
            if node['nodeId'] == nodeId:
                ratio = (maxRatio - minRatio) / (count - 1) * i + minRatio
                node[param] = template_nodes[j][param] * ratio
                break
        print(generate_node_config(nodes))

def generate_set_5():
    """
    Similar to generate_set_1 - vary one node at a time, one parameter at a time
    """
    generateAllParamSingleVariations(convergeEcosystem3Nodes, 50, 150, 5)

def generate_set_6():
    generatePairVariations(convergeEcosystem3Nodes, 'X', 50, 150, 10)

def generate_set_7():
    generateTripleVariations(convergeEcosystem3Nodes, 'X', 50, 150, 10)

def generate_set_9():
    """
    Generate single-parameter variations on Convergence ecosystem #2
    """
    generateAllParamSingleVariations(
            parse_node_config(convergence_node_configs[1]), 50, 150, 5)

def generate_set_10():
    """
    Generate single-parameter variations on Convergence ecosystem #4
    """
    generateAllParamSingleVariations(
            parse_node_config(convergence_node_configs[3]), 50, 150, 5)

def generate_set_11():
    """
    Generate single-parameter variations on Convergence ecosystem #5
    """
    generateAllParamSingleVariations(
            parse_node_config(convergence_node_configs[4]), 50, 150, 5)

def generate_set_12():
    """
    Generate random variations on Convergence ecosystem #2 (6 species)
    """
    nodes = parse_node_config(convergence_node_configs[1])
    generate_random_variations(nodes, ('initialBiomass', 'K', 'R', 'X'),
                               50, 150, 1000)

def generate_per_unit_biomass_variations():
    nodes = parse_node_config(convergence_node_configs[1])
    generate_random_variations(nodes, ('perUnitBiomass',), 50, 150, 100)


def generate_gaussian_mixture_variations(template_nodes, distribution, count):
    """
    Generate 'count' node configs based on the given GMM distribution.

    The 'distribution' argument is a data structure returned by
    parse_weka_em_output().

    Attributes are treated independently; Weka's EM clusterer does not estimate
    multivariate Gaussians.
    """

    nodes = deepcopy(template_nodes)

    priors = [component['prior'] for component in distribution]
    cumulative_priors = list(itertools.accumulate(priors))

    # Count the number of times each component was chosen (for testing)
    count_k = [0, 0]

    for i in range(count):

        # Choose a component based on the prior probabilities
        rand = random.random() * cumulative_priors[-1]
        k = bisect.bisect(cumulative_priors, rand)
        count_k[k] += 1
        component_nodes = distribution[k]['nodes']

        # Draw parameter values from the Gaussian distribution defined by
        # component_nodes.
        for node in nodes:
            nodeId = node['nodeId']
            for param_name, dist_params in component_nodes[nodeId].items():
                node[param_name] = random.gauss(
                        dist_params['mean'], dist_params['stdDev'])
        print(generate_node_config(nodes))

    # Print number of times each component was chosen (for testing - proportions
    # should match priors)
    #print(count_k)


def make_base_config_from_species_list(species_id_list,
                                       basal_biomass=1000.0, non_basal_biomass=1000.0, sort=True):
    species_data = util.get_species_data()
    nodes = []

    for species_id in species_id_list:
        species = species_data[species_id]
        if len(species['node_id_list']) > 1:
            raise RuntimeError("Species with multiple nodes not handled yet")
        node = {
            'nodeId': species['node_id_list'][0],
            'perUnitBiomass': species['biomass'],
        }
        if species['organism_type'] == 1:
            # plant
            node['initialBiomass'] = basal_biomass
            node['K'] = species['carrying_capacity']
            node['R'] = species['growth_rate']
        else:
            # animal
            node['initialBiomass'] = non_basal_biomass
            node['X'] = species['metabolism']

        nodes.append(node)

    if sort:
        # Sort by node ID to avoid triggering bug in unpatched ATNEngine
        nodes.sort(key=lambda n: n['nodeId'])
    # Otherwise, it's assumed speciesIdList is sorted as desired

    return nodes


def make_base_config_from_node_list(node_id_list,
                                       basal_biomass=1000.0, non_basal_biomass=1000.0, sort=True):
    species_data = util.get_species_data()

    # Build a version of species_data indexed by node ID
    species_data_by_node_id = {}
    for species_id, species in species_data.items():
        if species_id >= 1006:
            # It's a plant species not included in food web,
            # most of which break the 1-1 relationship between node ID and species ID
            continue
        node_id = species['node_id_list'][0]
        assert node_id not in species_data_by_node_id
        species_data_by_node_id[node_id] = species

    nodes = []

    for node_id in node_id_list:

        species = species_data_by_node_id[node_id]

        assert len(species['node_id_list']) == 1
        node = {
            'nodeId': species['node_id_list'][0],
            'perUnitBiomass': species['biomass'],
        }
        if species['organism_type'] == 1:
            # plant
            node['initialBiomass'] = basal_biomass
            node['K'] = species['carrying_capacity']
            node['R'] = species['growth_rate']
        else:
            # animal
            node['initialBiomass'] = non_basal_biomass
            node['X'] = species['metabolism']

        nodes.append(node)

    if sort:
        # Sort by node ID to avoid triggering bug in unpatched ATNEngine
        nodes.sort(key=lambda n: n['nodeId'])
    # Otherwise, it's assumed speciesIdList is sorted as desired

    return nodes


def generate_set_16():
    """
    Generate node configs for an algorithmically-generated 7-species food web.
    Only initial biomass is varied.
    """
    species_ids = [int(i) for i in '9 19 32 57 61 64 89'.split()]
    template_nodes = make_base_config_from_species_list(species_ids)
    generate_random_variations(template_nodes, ['initialBiomass'], 20, 200, 1000)

def generate_set_17():
    """
    Generate node configs for an algorithmically-generated 7-species food web.
    Only initial biomass is varied.
    """
    species_ids = [int(i) for i in '9 19 32 57 61 64 89'.split()]
    template_nodes = make_base_config_from_species_list(species_ids)
    generate_random_variations(template_nodes, ['initialBiomass'], 10, 300, 2000)

def generate_set_18():
    """
    Generate node configs for an algorithmically-generated 7-species food web.
    Only initial biomass is varied.
    """
    species_ids = [int(i) for i in '8 9 31 52 55 1002 1005'.split()]
    template_nodes = make_base_config_from_species_list(species_ids)
    generate_random_variations(template_nodes, ['initialBiomass'], 10, 300, 2000)

def generate_set_19():
    """
    Generate node configs for an algorithmically-generated 5-species food web.
    Only initial biomass is varied.
    """
    species_ids = [int(i) for i in '9 10 12 25 89'.split()]
    template_nodes = make_base_config_from_species_list(species_ids)
    generate_random_variations(template_nodes, ['initialBiomass'], 10, 300, 2000)

def generate_set_20():
    """
    Generate node configs for an algorithmically-generated 5-species food web.
    Only initial biomass is varied.
    This one gives 10x as much initial biomass to the basal species.
    """
    species_ids = [int(i) for i in '15 17 26 77 1002'.split()]
    template_nodes = make_base_config_from_species_list(species_ids)
    generate_random_variations(template_nodes, ['initialBiomass'], 10, 300, 2000)

def generate_set_21():
    species_ids = [int(i) for i in '15 17 26 77 1002'.split()]
    template_nodes = make_base_config_from_species_list(species_ids)
    generate_random_variations(template_nodes, ['initialBiomass', 'K', 'R', 'X'],
                               33, 300, 3000)

def generate_set_22():
    species_ids = [int(i) for i in '42 31 5 85 1005'.split()]
    template_nodes = make_base_config_from_species_list(species_ids)
    generate_random_variations(template_nodes, ['initialBiomass', 'K', 'R', 'X'],
                               50, 200, 1000)
generator_functions[22] = generate_set_22

def generate_set_23():
    species_ids = [int(i) for i in '72 33 1003 28 51'.split()]
    template_nodes = make_base_config_from_species_list(species_ids)
    generate_random_variations(template_nodes, ['initialBiomass', 'K', 'R', 'X'],
                               50, 200, 1000)
generator_functions[23] = generate_set_23

def generate_set_24():
    species_ids = [int(i) for i in '1001 87 75 14 33'.split()]
    template_nodes = make_base_config_from_species_list(species_ids)
    generate_random_variations(template_nodes, ['initialBiomass', 'K', 'R', 'X'],
                               50, 200, 1000)
generator_functions[24] = generate_set_24

def generate_set_25():
    species_ids = [int(i) for i in '16 82 83 1004 86'.split()]
    template_nodes = make_base_config_from_species_list(species_ids)
    generate_random_variations(template_nodes, ['initialBiomass', 'K', 'R', 'X'],
                               50, 200, 1000)
generator_functions[25] = generate_set_25

def generate_set_26():
    species_ids = [int(i) for i in '65 66 51 85 6 63 74 1003 1004 45 31'.split()]
    template_nodes = make_base_config_from_species_list(species_ids)
    generate_random_variations(template_nodes, ['initialBiomass', 'K', 'R', 'X'],
                               50, 200, 1000)
generator_functions[26] = generate_set_26

def generate_set_27():
    species_ids = [int(i) for i in '34 22 70 28 40 9 47 1004 1005 14 45'.split()]
    template_nodes = make_base_config_from_species_list(species_ids)
    generate_random_variations(template_nodes, ['initialBiomass', 'K', 'R', 'X'],
                               50, 200, 1000)
generator_functions[27] = generate_set_27

def generate_set_28():
    species_ids = [int(i) for i in '83 85 6 39 8 44 1002 55 1004 74 31'.split()]
    template_nodes = make_base_config_from_species_list(species_ids)
    generate_random_variations(template_nodes, ['initialBiomass', 'K', 'R', 'X'],
                               50, 200, 1000)
generator_functions[28] = generate_set_28

def generate_set_29():
    species_ids = [int(i) for i in '64 16 26 69 87 1001 42 1003 45 31'.split()]
    template_nodes = make_base_config_from_species_list(species_ids)
    generate_random_variations(template_nodes, ['initialBiomass', 'K', 'R', 'X'],
                               50, 200, 1000)
generator_functions[29] = generate_set_29

def generate_set_30():
    species_ids = [int(i) for i in '48 33 82 52 25 17 1001 1003 13 46'.split()]
    template_nodes = make_base_config_from_species_list(species_ids)
    generate_random_variations(template_nodes, ['initialBiomass', 'K', 'R', 'X'],
                               50, 200, 1000)
generator_functions[30] = generate_set_30

def generate_set_31():
    species_ids = [int(i) for i in '48 66 27 4 85 1001 10 11 1004 45'.split()]
    template_nodes = make_base_config_from_species_list(species_ids)
    generate_random_variations(template_nodes, ['initialBiomass', 'K', 'R', 'X'],
                               50, 200, 1000)
generator_functions[31] = generate_set_31

def generate_set_32():
    species_ids = [int(i) for i in '2 42 5 72 83 1002 1003 74 14 53'.split()]
    template_nodes = make_base_config_from_species_list(species_ids)
    generate_random_variations(template_nodes, ['initialBiomass', 'K', 'R', 'X'],
                               50, 200, 1000)
generator_functions[32] = generate_set_32

def generate_set_33():
    species_ids = [int(i) for i in '2 42 5 72 83 1002 1003 74 14 53'.split()]
    template_nodes = make_base_config_from_species_list(species_ids)
    generate_random_variations(template_nodes, ['initialBiomass', 'K', 'R', 'X'],
                               50, 200, 1000)
generator_functions[33] = generate_set_33

def generate_set_34():
    species_ids = [int(i) for i in '85 70 71 40 41 26 59 1004 1005'.split()]
    template_nodes = make_base_config_from_species_list(species_ids)
    generate_random_variations(template_nodes, ['initialBiomass', 'K', 'R', 'X'],
                               50, 200, 1000)
generator_functions[34] = generate_set_34

def generate_set_35():
    species_ids = [int(i) for i in '16 21 38 55 1002 1003 28 46 31'.split()]
    template_nodes = make_base_config_from_species_list(species_ids)
    generate_random_variations(template_nodes, ['initialBiomass', 'K', 'R', 'X'],
                               50, 200, 100)
generator_functions[35] = generate_set_35

def generate_set_36():
    species_ids = [int(i) for i in '16 17 53 1001 1003 77 14 21'.split()]
    template_nodes = make_base_config_from_species_list(species_ids)
    generate_random_variations(template_nodes, ['initialBiomass', 'K', 'R', 'X'],
                               50, 200, 100)
generator_functions[36] = generate_set_36

def generate_set_37():
    species_ids = [int(i) for i in '16 17 53 1001 1003 77 14 21'.split()]
    template_nodes = make_base_config_from_species_list(species_ids)
    generate_random_variations(template_nodes, ['initialBiomass', 'K', 'R', 'X'],
                               50, 200, 100)
generator_functions[37] = generate_set_37

def generate_set_38():
    species_ids = [int(i) for i in '80 1 11 69 27 71 1001 1003'.split()]
    template_nodes = make_base_config_from_species_list(species_ids)
    generate_random_variations(template_nodes, ['initialBiomass', 'K', 'R', 'X'],
                               50, 200, 100)
generator_functions[38] = generate_set_38

def generate_set_39():
    species_ids = [int(i) for i in '80 49 55 8 1002 15'.split()]
    template_nodes = make_base_config_from_species_list(species_ids)
    generate_random_variations(template_nodes, ['initialBiomass', 'K', 'R', 'X'],
                               50, 200, 100)
generator_functions[39] = generate_set_39

def generate_set_40():
    species_ids = [int(i) for i in '2 42 5 72 83 1002 1003 74 14 53'.split()]
    nodes = make_base_config_from_species_list(species_ids)
    for i in range(10):
        print(generate_node_config(nodes))
        random.shuffle(nodes)
generator_functions[40] = generate_set_40

def generate_set_41():
    species_ids = [int(i) for i in '2 42 5 72 83 1002 1003 74 14 53'.split()]
    nodes = make_base_config_from_species_list(species_ids)
    for i in range(10):
        print(generate_node_config(nodes))
        nonBasalNodes = nodes[2:]
        random.shuffle(nonBasalNodes)
        nodes = nodes[0:2] + nonBasalNodes
generator_functions[41] = generate_set_41

def generate_set_42():
    nodes = parse_node_config(convergence_node_configs[0])
    for i in range(10):
        print(generate_node_config(nodes))
        nonBasalNodes = nodes[1:]
        random.shuffle(nonBasalNodes)
        nodes = nodes[0:1] + nonBasalNodes
generator_functions[42] = generate_set_42

def generate_set_43():
    # Topologically sorted version of set 29
    species_ids = [int(i) for i in '1003 1001 31 45 87 69 16 26 42 64'.split()]
    template_nodes = make_base_config_from_species_list(species_ids, sort=False)
    generate_random_variations(template_nodes, ['initialBiomass', 'K', 'R', 'X'],
                               50, 200, 1000)
generator_functions[43] = generate_set_43

def generate_set_44():
    species_ids = [int(i) for i in '72 33 1003 28 51'.split()]
    template_nodes = make_base_config_from_species_list(species_ids)
    sweepParamForNode(template_nodes, 51, 'initialBiomass', 5, 100, 1000)
generator_functions[44] = generate_set_44

def generate_set_45():
    species_ids = [int(i) for i in '72 33 1003 28 51'.split()]
    template_nodes = make_base_config_from_species_list(species_ids)
    sweepParamForNode(template_nodes, 51, 'X', 5, 100, 1000)
generator_functions[45] = generate_set_45

def generate_set_46():
    species_ids = [1005, 14, 31, 42, 2]
    template_nodes = make_base_config_from_species_list(species_ids)
    generate_random_variations(template_nodes, ['initialBiomass', 'K', 'R', 'X'],
                               50, 200, 1000)
generator_functions[46] = generate_set_46

def generate_set_47():
    template_nodes = parse_node_config(convergence_node_configs[0])
    generate_random_variations(template_nodes, ['initialBiomass', 'K', 'R', 'X'],
                               50, 150, 1000)
generator_functions[47] = generate_set_47

def generate_set_48():
    template_nodes = parse_node_config(convergence_node_configs[1])
    generate_random_variations(template_nodes, ['initialBiomass', 'K', 'R', 'X'],
                               50, 150, 1000)
generator_functions[48] = generate_set_48

def generate_set_49():
    species_ids = [int(i) for i in '80 51 52 71 1001 75'.split()]
    template_nodes = make_base_config_from_species_list(species_ids)
    generate_random_variations(template_nodes, ['initialBiomass', 'K', 'R', 'X'],
                               50, 200, 100)
generator_functions[49] = generate_set_49

def generate_set_50():
    template_nodes = parse_node_config(convergence_node_configs[2])
    generate_random_variations(template_nodes, ['initialBiomass', 'K', 'R', 'X'],
                               50, 150, 1000)
generator_functions[50] = generate_set_50

def generate_set_51():
    # Variations on set 47, sim 90
    template_nodes = parse_node_config("5,[5],1555.63,1.0,1,K=11091.4,0,[14],1071.01,20.0,1,X=0.254849,0,[31],1844.15,0.0075,1,X=0.517565,0,[42],133.96,0.205,1,X=0.726891,0,[70],2110.84,13.0,1,X=0.194138,0")
    generate_random_variations(template_nodes, ['K', 'X'], 50, 150, 100)
generator_functions[51] = generate_set_51

def generate_set_52():
    # Variations on set 50, sim 100
    template_nodes = parse_node_config("11,[2],645.546,528.0,2,K=1660.64,R=1.0,0,[3],599.66,528.0,1,K=4441.54,0,[4],595.662,528.0,1,K=2754.94,0,[5],1426.75,1.0,1,K=2084.45,0,[7],639.183,816.0,1,K=4015.18,0,[49],1511.23,0.355,1,X=1.0,0,[55],739.104,0.213,1,X=0.496037,0,[61],392.821,54.0,1,X=0.00999599,0,[74],924.06,50.0,1,X=0.115569,0,[82],525.34,50.0,1,X=0.376351,0,[83],233.019,103.0,1,X=0.180538,0")
    generate_random_variations(template_nodes, ['K', 'X'], 50, 150, 100)
generator_functions[52] = generate_set_52

def generate_set_53():
    """ Like set 42, but shuffle all nodes, not just basal """
    nodes = parse_node_config(convergence_node_configs[0])
    for i in range(10):
        print(generate_node_config(nodes))
        random.shuffle(nodes)
generator_functions[53] = generate_set_53

def generate_set_54():
    template_nodes = make_base_config_from_species_list([73, 1003, 61, 55, 33])
    generate_random_variations(template_nodes, ['initialBiomass'], 25, 175, 1000)
generator_functions[54] = generate_set_54

def generate_set_55():
    template_nodes = make_base_config_from_species_list([73, 1003, 61, 55, 33])
    sweepParamForNode(template_nodes, 3, 'R', 10, 300, 100)
generator_functions[55] = generate_set_55

def generate_set_56():
    template_nodes = make_base_config_from_species_list([73, 1003, 61, 55, 33])
    sweepParamForNode(template_nodes, 3, 'initialBiomass', 50, 500, 100)
generator_functions[56] = generate_set_56

def generate_set_57():
    template_nodes = make_base_config_from_species_list([8, 4, 1002, 36, 14])
    generate_random_variations(template_nodes, ['initialBiomass'], 25, 175, 1000)
generator_functions[57] = generate_set_57

def generate_set_58():
    template_nodes = make_base_config_from_species_list([65, 50, 1003, 55, 33])
    generate_random_variations(template_nodes, ['initialBiomass'], 25, 175, 1000)
generator_functions[58] = generate_set_58

def generate_set_59():
    template_nodes = make_base_config_from_species_list([1002, 36, 14, 46, 31])
    generate_random_variations(template_nodes, ['initialBiomass'], 25, 175, 1000)
generator_functions[59] = generate_set_59

def generate_set_60():
    template_nodes = make_base_config_from_species_list(
            [66, 83, 82, 53, 71, 88, 1001, 7, 1004, 1005])
    generate_random_variations(template_nodes, ['initialBiomass'], 25, 175, 1000)
generator_functions[60] = generate_set_60

def generate_set_61():
    template_nodes = make_base_config_from_species_list(
            [88, 2, 4, 21, 87, 8, 1001, 1002, 1003, 14]
            )
    generate_random_variations(template_nodes, ['initialBiomass'], 25, 175, 1000)
generator_functions[61] = generate_set_61

def generate_set_62():
    template_nodes = make_base_config_from_species_list(
            [49, 83, 53, 28, 1001, 42, 1003, 1004, 85, 44]
            )
    generate_random_variations(template_nodes, ['initialBiomass'], 25, 175, 1000)
generator_functions[62] = generate_set_62

def generate_set_63():
    template_nodes = make_base_config_from_species_list(
            [80, 66, 1003, 4, 31]
            )
    generate_random_variations(template_nodes, ['initialBiomass'], 25, 175, 1000)
generator_functions[63] = generate_set_63

def generate_set_64():
    template_nodes = make_base_config_from_species_list(
            [80, 49, 82, 50, 69, 71, 88, 1001, 1003, 1005]
            )
    generate_random_variations(template_nodes, ['initialBiomass'], 25, 175, 1000)
generator_functions[64] = generate_set_64

def generate_set_65():
    origNodes = make_base_config_from_species_list(
            [53, 73, 74, 80, 1005]
            )
    print(generate_node_config(origNodes))
generator_functions[65] = generate_set_65

def generate_set_66():
    origNodes = make_base_config_from_species_list(
            [47, 49, 83, 86, 1003]
            )
    print(generate_node_config(origNodes))
generator_functions[66] = generate_set_66

def generate_set_67():
    template_nodes = make_base_config_from_species_list(
            [39, 80, 31, 72, 1003]
            )
    generate_random_variations(template_nodes, ['initialBiomass', 'K', 'R', 'X'],
                               50, 150, 1000)
generator_functions[67] = generate_set_67

def generate_set_68():
    template_nodes = make_base_config_from_species_list(
            [49, 4, 18, 50, 36, 9, 85, 14, 8, 1002]
            )
    generate_random_variations(template_nodes, ['initialBiomass', 'K', 'R', 'X'],
                               50, 150, 1000)
generator_functions[68] = generate_set_68

def generate_set_69():
    template_nodes = make_base_config_from_species_list(
            [3, 49, 41, 86, 47, 61, 83, 33, 1004, 1005]
            )
    generate_random_variations(template_nodes, ['initialBiomass', 'K', 'R', 'X'],
                               50, 150, 1000)
generator_functions[69] = generate_set_69


def vary_initial_biomass_species_ids(species_ids):
    template_nodes = make_base_config_from_species_list(species_ids)
    generate_random_variations(template_nodes, ['initialBiomass'], 25, 175, 1000)


def vary_initial_biomass(node_ids):
    template_nodes = make_base_config_from_node_list(node_ids)
    generate_random_variations(template_nodes, ['initialBiomass'], 25, 175, 1000)


def vary_x_k(node_config):
    template_nodes = parse_node_config(node_config)
    generate_random_variations(template_nodes, ['X', 'K'], 50, 150, 1000)


# 5-species initial biomass variations
generator_functions[70] = lambda: vary_initial_biomass_species_ids([15, 17, 55, 80, 1002])
generator_functions[71] = lambda: vary_initial_biomass_species_ids([2, 5, 57, 61, 1005])
generator_functions[72] = lambda: vary_initial_biomass_species_ids([26, 40, 49, 73, 1004])
generator_functions[73] = lambda: vary_initial_biomass_species_ids([5, 14, 67, 85, 1005])
generator_functions[74] = lambda: vary_initial_biomass_species_ids([53, 74, 82, 86, 1004])

# 5-species X and K variations
generator_functions[75] = lambda: vary_x_k('5,[2],408.544,20.0,2,K=10000.0,R=1.0,0,[15],388.199,0.071,1,X=0.00412167,0,[17],256.225,0.17,1,X=0.00331341,0,[55],866.213,0.213,1,X=0.344497,0,[80],736.208,41.5,1,X=0.0922079,0')
generator_functions[76] = lambda: vary_x_k('5,[5],541.624,40.0,2,K=10000.0,R=1.0,0,[57],460.599,4.2,1,X=0.163481,0,[61],274.932,54.0,1,X=0.00361033,0,[67],444.404,9.6,1,X=0.132957,0,[70],304.869,13.0,1,X=0.123252,0')
generator_functions[77] = lambda: vary_x_k('5,[4],1090.86,20.0,2,K=10000.0,R=1.0,0,[26],724.713,0.011,1,X=0.722657,0,[40],640.404,0.325,1,X=0.309963,0,[49],1242.61,0.355,1,X=0.303196,0,[73],396.618,17.0,1,X=0.115257,0')
generator_functions[78] = lambda: vary_x_k('5,[5],262.045,40.0,2,K=10000.0,R=1.0,0,[14],1076.64,20.0,1,X=0.00100607,0,[67],1204.03,9.6,1,X=0.132957,0,[85],492.77,108.0,1,X=0.072598,0,[94],530.41,1550.0,1,X=0.037299,0')
generator_functions[79] = lambda: vary_x_k('5,[4],756.561,20.0,2,K=10000.0,R=1.0,0,[74],667.793,23.8,1,X=0.105959,0,[82],1521.54,50.0,1,X=0.0880112,0,[86],1060.07,156.0,1,X=0.0662215,0,[89],1440.2,470.0,1,X=0.0502639,0')

# 10-species initial biomass variations
generator_functions[80] = lambda: vary_initial_biomass_species_ids([14, 18, 31, 32, 49, 57, 63, 69, 1002, 1004])
generator_functions[81] = lambda: vary_initial_biomass_species_ids([2, 21, 43, 49, 50, 53, 69, 86, 1003, 1004])
generator_functions[82] = lambda: vary_initial_biomass_species_ids([3, 15, 27, 33, 38, 53, 69, 85, 1002, 1004])
generator_functions[83] = lambda: vary_initial_biomass_species_ids([31, 44, 45, 47, 49, 50, 66, 75, 1001, 1005])
generator_functions[84] = lambda: vary_initial_biomass_species_ids([53, 55, 59, 71, 74, 86, 87, 88, 1004, 1005])

# 15-species initial biomass variations
generator_functions[85] = lambda: vary_initial_biomass_species_ids([11, 31, 39, 43, 49, 51, 66, 69, 72, 80, 82, 88, 1001, 1003, 1004])
generator_functions[86] = lambda: vary_initial_biomass_species_ids([15, 16, 22, 24, 26, 29, 31, 49, 53, 73, 74, 80, 1002, 1004, 1005])
generator_functions[87] = lambda: vary_initial_biomass_species_ids([16, 30, 31, 38, 49, 50, 53, 57, 66, 67, 83, 86, 1001, 1003, 1005])
generator_functions[88] = lambda: vary_initial_biomass_species_ids([2, 3, 15, 18, 22, 34, 42, 49, 50, 52, 57, 67, 1002, 1004, 1005])
generator_functions[89] = lambda: vary_initial_biomass_species_ids([4, 5, 27, 45, 53, 59, 61, 63, 67, 80, 82, 86, 1001, 1004, 1005])

# 10-species X and K variations
generator_functions[90] = lambda: vary_x_k('10,[2],907.82,20.0,2,K=10000.0,R=1.0,0,[4],1222.14,20.0,2,K=10000.0,R=1.0,0,[14],771.772,20.0,1,X=0.00100607,0,[18],250.02,0.00014,1,X=0.0195594,0,[31],854.717,0.0075,1,X=0.795271,0,[32],856.17,0.13,1,X=0.0162989,0,[49],938.492,0.355,1,X=0.303196,0,[57],1220.21,4.2,1,X=0.163481,0,[63],956.904,7.85,1,X=0.139818,0,[69],1390.3,12.5,1,X=0.124467,0')
generator_functions[91] = lambda: vary_x_k('10,[3],1026.9,20.0,2,K=10000.0,R=1.0,0,[4],1048.15,20.0,2,K=10000.0,R=1.0,0,[21],1170.37,0.2,1,X=0.00318149,0,[43],313.774,0.03,1,X=0.562341,0,[49],280.525,0.355,1,X=0.303196,0,[50],1419.12,0.349,1,X=0.304491,0,[69],1079.11,12.5,1,X=0.124467,0,[70],1568.36,13.0,1,X=0.123252,0,[86],1517.79,156.0,1,X=0.0662215,0,[89],481.552,470.0,1,X=0.0502639,0')
generator_functions[92] = lambda: vary_x_k('10,[2],712.521,20.0,2,K=10000.0,R=1.0,0,[4],1657.62,20.0,2,K=10000.0,R=1.0,0,[15],375.247,0.071,1,X=0.00412167,0,[27],440.093,0.009,1,X=0.759836,0,[33],515.328,0.4,1,X=0.294283,0,[38],1587.3,0.085,1,X=0.0181255,0,[53],400.787,2.8,1,X=0.180922,0,[69],1683.99,12.5,1,X=0.124467,0,[85],256.855,108.0,1,X=0.072598,0,[89],868.82,470.0,1,X=0.0502639,0')
generator_functions[93] = lambda: vary_x_k('10,[5],892.537,40.0,2,K=10000.0,R=1.0,0,[7],271.895,40.0,2,K=10000.0,R=1.0,0,[31],1325.14,0.0075,1,X=0.795271,0,[44],730.286,0.028,1,X=0.0239252,0,[45],1229.58,0.425,1,X=0.289857,0,[47],1426.91,5.45,1,X=0.153173,0,[49],1360.18,0.355,1,X=0.303196,0,[50],1399.09,0.349,1,X=0.304491,0,[66],1106.88,10.2,1,X=0.130957,0,[92],1198.57,1250.0,1,X=0.0393598,0')
generator_functions[94] = lambda: vary_x_k('10,[4],899.75,20.0,2,K=10000.0,R=1.0,0,[5],1461.61,40.0,2,K=10000.0,R=1.0,0,[55],920.492,0.213,1,X=0.344497,0,[71],1542.23,4.99,1,X=0.156587,0,[74],1383.73,23.8,1,X=0.105959,0,[86],1184.85,156.0,1,X=0.0662215,0,[87],622.142,112.0,1,X=0.0719409,0,[89],529.502,470.0,1,X=0.0502639,0,[91],267.641,388.0,1,X=0.00220515,0,[95],821.795,5520.0,1,X=0.0271516,0')

# 15-species X and K variations
generator_functions[95] = lambda: vary_x_k('15,[3],345.236,20.0,2,K=10000.0,R=1.0,0,[4],979.309,20.0,2,K=10000.0,R=1.0,0,[7],946.448,40.0,2,K=10000.0,R=1.0,0,[11],620.562,4e-06,1,X=0.0475743,0,[31],1145.22,0.0075,1,X=0.795271,0,[39],973.271,0.085,1,X=0.433437,0,[43],290.491,0.03,1,X=0.562341,0,[49],1705.77,0.355,1,X=0.303196,0,[51],656.169,2.05,1,X=0.195588,0,[66],485.421,10.2,1,X=0.130957,0,[69],1263.74,12.5,1,X=0.124467,0,[72],1516.83,0.3,1,X=0.316228,0,[80],1414.73,41.5,1,X=0.0922079,0,[82],1349.92,50.0,1,X=0.0880112,0,[91],300.972,388.0,1,X=0.00220515,0')
generator_functions[96] = lambda: vary_x_k('15,[2],1224.54,20.0,2,K=10000.0,R=1.0,0,[4],1269.58,20.0,2,K=10000.0,R=1.0,0,[5],1205.86,40.0,2,K=10000.0,R=1.0,0,[15],1239.14,0.071,1,X=0.00412167,0,[16],1315.66,0.9,1,X=0.00218437,0,[22],1007.89,0.68,1,X=0.257723,0,[24],261.373,0.005,1,X=0.00800102,0,[26],363.522,0.011,1,X=0.722657,0,[29],655.127,0.035,1,X=0.541082,0,[31],1637.7,0.0075,1,X=0.795271,0,[49],427.97,0.355,1,X=0.303196,0,[73],1530.05,17.0,1,X=0.115257,0,[74],916.42,23.8,1,X=0.105959,0,[80],1342.31,41.5,1,X=0.0922079,0,[89],1318.0,470.0,1,X=0.0502639,0')
generator_functions[97] = lambda: vary_x_k('15,[3],612.341,20.0,2,K=10000.0,R=1.0,0,[5],1102.86,40.0,2,K=10000.0,R=1.0,0,[7],905.292,40.0,2,K=10000.0,R=1.0,0,[16],936.184,0.9,1,X=0.00218437,0,[30],1203.72,0.029,1,X=0.567128,0,[31],251.104,0.0075,1,X=0.795271,0,[38],1223.36,0.085,1,X=0.0181255,0,[49],1011.56,0.355,1,X=0.303196,0,[50],323.838,0.349,1,X=0.304491,0,[57],1288.02,4.2,1,X=0.163481,0,[66],789.805,10.2,1,X=0.130957,0,[83],1312.25,103.0,1,X=0.0734634,0,[86],349.541,156.0,1,X=0.0662215,0,[89],1114.34,470.0,1,X=0.0502639,0,[94],1539.7,1550.0,1,X=0.037299,0')
generator_functions[98] = lambda: vary_x_k('15,[2],711.901,20.0,2,K=10000.0,R=1.0,0,[4],974.336,20.0,2,K=10000.0,R=1.0,0,[5],629.732,40.0,2,K=10000.0,R=1.0,0,[15],1148.67,0.071,1,X=0.00412167,0,[18],1220.46,0.00014,1,X=0.0195594,0,[22],1005.17,0.68,1,X=0.257723,0,[34],383.387,0.0709,1,X=0.0189664,0,[42],587.471,0.205,1,X=0.34781,0,[49],299.732,0.355,1,X=0.303196,0,[50],1268.74,0.349,1,X=0.304491,0,[52],1700.41,7.0,1,X=0.143882,0,[53],717.439,2.8,1,X=0.180922,0,[57],1478.02,4.2,1,X=0.163481,0,[70],1173.33,13.0,1,X=0.123252,0,[94],1330.07,1550.0,1,X=0.037299,0')
generator_functions[99] = lambda: vary_x_k('15,[4],945.8,20.0,2,K=10000.0,R=1.0,0,[5],630.907,40.0,2,K=10000.0,R=1.0,0,[7],1251.03,40.0,2,K=10000.0,R=1.0,0,[27],750.751,0.009,1,X=0.759836,0,[45],1230.77,0.425,1,X=0.289857,0,[59],1151.0,3.35,1,X=0.172989,0,[61],640.964,54.0,1,X=0.00361033,0,[63],1282.38,7.85,1,X=0.139818,0,[67],1170.44,9.6,1,X=0.132957,0,[80],634.219,41.5,1,X=0.0922079,0,[82],1332.68,50.0,1,X=0.0880112,0,[86],253.817,156.0,1,X=0.0662215,0,[89],1355.82,470.0,1,X=0.0502639,0,[94],1014.92,1550.0,1,X=0.037299,0,[95],1434.45,5520.0,1,X=0.0271516,0')

generator_functions[100] = lambda: vary_initial_biomass_species_ids([2, 3, 42, 52, 53, 69, 75, 86, 1001, 1005])
generator_functions[101] = lambda: vary_x_k('10,[5],1539.57,40.0,2,K=10000.0,R=1.0,0,[7],841.602,40.0,2,K=10000.0,R=1.0,0,[42],597.749,0.205,1,X=0.34781,0,[52],928.551,7.0,1,X=0.143882,0,[53],395.806,2.8,1,X=0.180922,0,[69],1625.66,12.5,1,X=0.124467,0,[70],1096.04,13.0,1,X=0.123252,0,[86],1192.29,156.0,1,X=0.0662215,0,[89],341.895,470.0,1,X=0.0502639,0,[92],1612.24,1250.0,1,X=0.0393598,0')

# 25 additional 5-species food webs, initial biomass
for set_num, species_ids in enumerate([
    [2, 31, 55, 88, 1001],
    [3, 14, 42, 45, 1001],
    [3, 42, 69, 71, 1004],
    [5, 31, 49, 50, 1005],
    [5, 45, 53, 86, 1004],
    [5, 45, 83, 85, 1004],
    [8, 9, 55, 80, 1002],
    [8, 9, 55, 88, 1002],
    [8, 15, 29, 77, 1002],
    [9, 15, 20, 29, 1002],
    [14, 20, 34, 57, 1005],
    [14, 20, 39, 85, 1001],
    [15, 17, 22, 26, 1002],
    [16, 31, 32, 57, 1004],
    [21, 49, 50, 85, 1003],
    [26, 27, 28, 49, 1004],
    [26, 49, 83, 86, 1004],
    [27, 44, 49, 55, 1004],
    [31, 44, 49, 50, 1003],
    [33, 42, 72, 80, 1004],
    [40, 49, 57, 61, 1004],
    [47, 55, 74, 88, 1004],
    [48, 70, 71, 86, 1001],
    [66, 70, 71, 80, 1001],
    [72, 80, 85, 88, 1003]
    ], start=102):

    # Python has late-binding closures, but I want to bind the current value
    # of species_id. Using default argument s=species_ids to get around the
    # problem.
    generator_functions[set_num] = lambda s=species_ids: vary_initial_biomass_species_ids(s)

# 25 additional 10-species food webs, initial biomass
for set_num, species_ids in enumerate([
    [2, 8, 9, 42, 71, 80, 86, 87, 1002, 1005],
    [2, 26, 49, 53, 61, 66, 71, 80, 1001, 1004],
    [2, 42, 45, 61, 66, 74, 80, 82, 1001, 1004],
    [3, 14, 16, 20, 42, 55, 80, 85, 1001, 1005],
    [3, 15, 16, 42, 52, 70, 71, 74, 1002, 1005],
    [3, 26, 27, 28, 38, 40, 49, 73, 1001, 1004],
    [3, 31, 33, 42, 61, 72, 80, 88, 1003, 1004],
    [5, 13, 16, 34, 49, 50, 55, 88, 1003, 1004],
    [5, 14, 27, 31, 47, 51, 69, 70, 1004, 1005],
    [5, 51, 52, 71, 75, 80, 85, 86, 1001, 1005],
    [7, 16, 33, 53, 64, 67, 82, 86, 1004, 1005],
    [8, 9, 16, 46, 50, 51, 65, 85, 1002, 1003],
    [14, 16, 32, 43, 69, 73, 77, 80, 1002, 1004],
    [14, 25, 42, 47, 48, 49, 50, 85, 1001, 1002],
    [14, 29, 33, 49, 56, 71, 74, 77, 1001, 1005],
    [14, 29, 55, 57, 61, 71, 72, 80, 1002, 1003],
    [15, 28, 40, 42, 49, 53, 55, 80, 1002, 1004],
    [16, 31, 32, 49, 50, 57, 72, 86, 1003, 1005],
    [26, 31, 38, 43, 46, 49, 50, 69, 1001, 1004],
    [26, 33, 43, 49, 53, 69, 73, 80, 1004, 1005],
    [27, 44, 49, 51, 53, 63, 73, 80, 1004, 1005],
    [28, 33, 44, 51, 73, 83, 85, 86, 1001, 1003],
    [30, 31, 49, 50, 64, 82, 83, 86, 1003, 1004],
    [31, 47, 49, 50, 69, 72, 73, 74, 1004, 1005],
    [42, 53, 61, 67, 73, 80, 82, 88, 1001, 1005]
    ], start=127):

    generator_functions[set_num] = lambda s=species_ids: vary_initial_biomass_species_ids(s)

# 25 additional 15-species food webs, initial biomass
for set_num, species_ids in enumerate([
    [2, 5, 14, 18, 21, 28, 45, 49, 50, 55, 59, 70, 1001, 1003, 1005],
    [2, 6, 13, 27, 31, 34, 38, 42, 51, 63, 66, 74, 1001, 1003, 1005],
    [2, 7, 16, 42, 53, 55, 57, 61, 64, 85, 86, 88, 1002, 1004, 1005],
    [2, 7, 26, 42, 45, 49, 53, 55, 66, 70, 86, 88, 1001, 1004, 1005],
    [2, 14, 31, 33, 36, 49, 50, 64, 69, 80, 85, 88, 1001, 1002, 1005],
    [3, 6, 9, 15, 21, 28, 51, 57, 61, 72, 73, 74, 1002, 1003, 1004],
    [3, 13, 23, 30, 31, 34, 42, 49, 50, 57, 59, 80, 1001, 1003, 1005],
    [3, 14, 25, 40, 42, 49, 50, 72, 74, 83, 85, 86, 1002, 1003, 1004],
    [4, 6, 47, 53, 66, 67, 69, 71, 80, 82, 83, 86, 1003, 1004, 1005],
    [4, 15, 24, 29, 31, 53, 65, 72, 77, 80, 85, 88, 1001, 1002, 1003],
    [5, 6, 27, 28, 45, 48, 49, 53, 57, 75, 85, 86, 1001, 1004, 1005],
    [5, 6, 31, 45, 51, 52, 55, 57, 59, 61, 67, 70, 1002, 1004, 1005],
    [5, 8, 9, 11, 36, 39, 48, 61, 73, 80, 85, 88, 1001, 1002, 1005],
    [5, 16, 28, 47, 49, 52, 55, 61, 63, 64, 83, 86, 1001, 1002, 1004],
    [6, 16, 27, 31, 40, 49, 63, 64, 71, 73, 77, 80, 1001, 1004, 1005],
    [7, 13, 20, 29, 30, 49, 50, 52, 55, 65, 82, 86, 1002, 1003, 1005],
    [8, 9, 10, 14, 17, 55, 59, 67, 71, 86, 87, 88, 1002, 1004, 1005],
    [11, 34, 36, 40, 49, 50, 55, 59, 71, 72, 80, 87, 1001, 1002, 1004],
    [13, 21, 25, 26, 41, 52, 55, 63, 74, 80, 85, 88, 1001, 1003, 1005],
    [14, 17, 29, 36, 49, 50, 52, 55, 59, 67, 70, 80, 1001, 1002, 1005],
    [14, 21, 26, 44, 48, 53, 55, 65, 70, 80, 85, 86, 1001, 1003, 1004],
    [14, 27, 33, 41, 44, 56, 61, 64, 82, 83, 86, 88, 1002, 1004, 1005],
    [15, 16, 27, 29, 38, 55, 59, 61, 80, 83, 85, 86, 1002, 1004, 1005],
    [26, 27, 31, 38, 43, 44, 47, 59, 69, 71, 86, 87, 1003, 1004, 1005],
    [31, 41, 46, 49, 50, 53, 56, 59, 64, 75, 83, 86, 1001, 1004, 1005]
    ], start=152):

    generator_functions[set_num] = lambda s=species_ids: vary_initial_biomass_species_ids(s)

#
# X and K variations for above 75 food webs
#

node_configs = [
'5,[7],1321.74,40.0,2,K=10000.0,R=1.0,0,[31],1529.69,0.0075,1,X=0.795271,0,[55],617.141,0.213,1,X=0.344497,0,[70],1654.48,13.0,1,X=0.123252,0,[91],284.386,388.0,1,X=0.00220515,0',
'5,[7],408.753,40.0,2,K=10000.0,R=1.0,0,[14],313.344,20.0,1,X=0.00100607,0,[42],703.076,0.205,1,X=0.34781,0,[45],303.308,0.425,1,X=0.289857,0,[53],417.556,2.8,1,X=0.180922,0',
'5,[4],1460.38,20.0,2,K=10000.0,R=1.0,0,[42],253.191,0.205,1,X=0.34781,0,[53],1044.01,2.8,1,X=0.180922,0,[69],961.987,12.5,1,X=0.124467,0,[71],279.596,4.99,1,X=0.156587,0',
'5,[5],259.887,40.0,2,K=10000.0,R=1.0,0,[31],1533.51,0.0075,1,X=0.795271,0,[49],381.641,0.355,1,X=0.303196,0,[50],303.357,0.349,1,X=0.304491,0,[67],1167.03,9.6,1,X=0.132957,0',
'5,[4],1156.82,20.0,2,K=10000.0,R=1.0,0,[45],1551.76,0.425,1,X=0.289857,0,[67],269.088,9.6,1,X=0.132957,0,[86],1138.2,156.0,1,X=0.0662215,0,[89],1009.93,470.0,1,X=0.0502639,0',
'5,[4],1729.14,20.0,2,K=10000.0,R=1.0,0,[45],1526.6,0.425,1,X=0.289857,0,[67],894.084,9.6,1,X=0.132957,0,[83],774.825,103.0,1,X=0.0734634,0,[85],490.369,108.0,1,X=0.072598,0',
'5,[2],916.269,20.0,2,K=10000.0,R=1.0,0,[8],1665.3,1.1,1,X=0.00207749,0,[9],585.165,0.071,1,X=0.00412167,0,[55],651.445,0.213,1,X=0.344497,0,[80],273.126,41.5,1,X=0.0922079,0',
'5,[2],270.779,20.0,2,K=10000.0,R=1.0,0,[8],861.598,1.1,1,X=0.00207749,0,[9],312.916,0.071,1,X=0.00412167,0,[55],717.406,0.213,1,X=0.344497,0,[91],1600.2,388.0,1,X=0.00220515,0',
'5,[2],1401.3,20.0,2,K=10000.0,R=1.0,0,[8],847.187,1.1,1,X=0.00207749,0,[15],317.628,0.071,1,X=0.00412167,0,[29],381.422,0.035,1,X=0.541082,0,[77],1255.83,38.5,1,X=0.093954,0',
'5,[2],1644.42,20.0,2,K=10000.0,R=1.0,0,[9],533.209,0.071,1,X=0.00412167,0,[15],339.473,0.071,1,X=0.00412167,0,[20],254.136,0.04,1,X=0.0218842,0,[29],1064.56,0.035,1,X=0.541082,0',
'5,[5],1000.0,40.0,2,K=10000.0,R=1.0,0,[14],1000.0,20.0,1,X=0.00100607,0,[20],1000.0,0.04,1,X=0.0218842,0,[34],1000.0,0.0709,1,X=0.0189664,0,[57],1000.0,4.2,1,X=0.163481,0',
'5,[7],399.263,40.0,2,K=10000.0,R=1.0,0,[14],408.152,20.0,1,X=0.00100607,0,[20],257.486,0.04,1,X=0.0218842,0,[39],1723.54,0.085,1,X=0.433437,0,[85],1343.07,108.0,1,X=0.072598,0',
'5,[2],317.463,20.0,2,K=10000.0,R=1.0,0,[15],688.783,0.071,1,X=0.00412167,0,[17],271.923,0.17,1,X=0.00331341,0,[22],1458.31,0.68,1,X=0.257723,0,[26],730.431,0.011,1,X=0.722657,0',
'5,[4],315.168,20.0,2,K=10000.0,R=1.0,0,[16],336.504,0.9,1,X=0.00218437,0,[31],1091.11,0.0075,1,X=0.795271,0,[32],649.379,0.13,1,X=0.0162989,0,[57],265.039,4.2,1,X=0.163481,0',
'5,[3],1367.63,20.0,2,K=10000.0,R=1.0,0,[21],1387.87,0.2,1,X=0.00318149,0,[49],1365.86,0.355,1,X=0.303196,0,[50],1232.12,0.349,1,X=0.304491,0,[85],687.277,108.0,1,X=0.072598,0',
'5,[4],479.47,20.0,2,K=10000.0,R=1.0,0,[26],319.344,0.011,1,X=0.722657,0,[27],832.252,0.009,1,X=0.759836,0,[28],667.723,0.01,1,X=0.740083,0,[49],770.056,0.355,1,X=0.303196,0',
'5,[4],1635.37,20.0,2,K=10000.0,R=1.0,0,[26],1474.67,0.011,1,X=0.722657,0,[49],394.288,0.355,1,X=0.303196,0,[83],432.041,103.0,1,X=0.0734634,0,[86],349.424,156.0,1,X=0.0662215,0',
'5,[4],872.54,20.0,2,K=10000.0,R=1.0,0,[27],1287.67,0.009,1,X=0.759836,0,[44],261.969,0.028,1,X=0.0239252,0,[49],1279.52,0.355,1,X=0.303196,0,[55],1533.26,0.213,1,X=0.344497,0',
'5,[3],1028.32,20.0,2,K=10000.0,R=1.0,0,[31],911.817,0.0075,1,X=0.795271,0,[44],1370.75,0.028,1,X=0.0239252,0,[49],814.597,0.355,1,X=0.303196,0,[50],1601.84,0.349,1,X=0.304491,0',
'5,[4],568.985,20.0,2,K=10000.0,R=1.0,0,[33],301.077,0.4,1,X=0.294283,0,[42],501.384,0.205,1,X=0.34781,0,[72],1401.65,0.3,1,X=0.316228,0,[80],1312.04,41.5,1,X=0.0922079,0',
'5,[4],436.935,20.0,2,K=10000.0,R=1.0,0,[40],1119.9,0.325,1,X=0.309963,0,[49],332.736,0.355,1,X=0.303196,0,[57],677.597,4.2,1,X=0.163481,0,[61],1739.19,54.0,1,X=0.00361033,0',
'5,[4],1172.41,20.0,2,K=10000.0,R=1.0,0,[47],712.497,5.45,1,X=0.153173,0,[55],497.883,0.213,1,X=0.344497,0,[74],1261.54,23.8,1,X=0.105959,0,[91],289.316,388.0,1,X=0.00220515,0',
'5,[7],776.824,40.0,2,K=10000.0,R=1.0,0,[48],1554.74,4.49,1,X=0.160775,0,[71],682.604,4.99,1,X=0.156587,0,[86],1556.52,156.0,1,X=0.0662215,0,[93],1413.69,1100.0,1,X=0.040638,0',
'5,[7],1434.36,40.0,2,K=10000.0,R=1.0,0,[66],573.448,10.2,1,X=0.130957,0,[71],759.51,4.99,1,X=0.156587,0,[80],1189.53,41.5,1,X=0.0922079,0,[93],1732.58,1100.0,1,X=0.040638,0',
'5,[3],273.609,20.0,2,K=10000.0,R=1.0,0,[72],274.956,0.3,1,X=0.316228,0,[80],557.807,41.5,1,X=0.0922079,0,[85],586.571,108.0,1,X=0.072598,0,[91],311.958,388.0,1,X=0.00220515,0',
'10,[2],1033.06,20.0,2,K=10000.0,R=1.0,0,[5],588.64,40.0,2,K=10000.0,R=1.0,0,[8],819.884,1.1,1,X=0.00207749,0,[9],1067.18,0.071,1,X=0.00412167,0,[42],385.257,0.205,1,X=0.34781,0,[70],310.91,13.0,1,X=0.123252,0,[71],1624.28,4.99,1,X=0.156587,0,[80],922.043,41.5,1,X=0.0922079,0,[86],484.123,156.0,1,X=0.0662215,0,[87],1014.36,112.0,1,X=0.0719409,0',
'10,[4],1694.3,20.0,2,K=10000.0,R=1.0,0,[7],407.367,40.0,2,K=10000.0,R=1.0,0,[26],501.224,0.011,1,X=0.722657,0,[49],434.172,0.355,1,X=0.303196,0,[61],465.607,54.0,1,X=0.00361033,0,[66],789.618,10.2,1,X=0.130957,0,[70],1289.47,13.0,1,X=0.123252,0,[71],296.533,4.99,1,X=0.156587,0,[80],676.205,41.5,1,X=0.0922079,0,[89],258.215,470.0,1,X=0.0502639,0',
'10,[4],961.455,20.0,2,K=10000.0,R=1.0,0,[7],929.851,40.0,2,K=10000.0,R=1.0,0,[42],457.335,0.205,1,X=0.34781,0,[45],413.964,0.425,1,X=0.289857,0,[61],353.535,54.0,1,X=0.00361033,0,[66],486.865,10.2,1,X=0.130957,0,[70],397.648,13.0,1,X=0.123252,0,[74],1626.85,23.8,1,X=0.105959,0,[80],538.148,41.5,1,X=0.0922079,0,[82],696.067,50.0,1,X=0.0880112,0',
'10,[5],274.569,40.0,2,K=10000.0,R=1.0,0,[7],274.129,40.0,2,K=10000.0,R=1.0,0,[14],365.554,20.0,1,X=0.00100607,0,[16],919.398,0.9,1,X=0.00218437,0,[20],1579.56,0.04,1,X=0.0218842,0,[42],1360.73,0.205,1,X=0.34781,0,[53],775.496,2.8,1,X=0.180922,0,[55],1207.89,0.213,1,X=0.344497,0,[80],904.837,41.5,1,X=0.0922079,0,[85],550.035,108.0,1,X=0.072598,0',
'10,[2],1029.3,20.0,2,K=10000.0,R=1.0,0,[5],906.596,40.0,2,K=10000.0,R=1.0,0,[15],958.999,0.071,1,X=0.00412167,0,[16],258.822,0.9,1,X=0.00218437,0,[42],922.191,0.205,1,X=0.34781,0,[52],397.216,7.0,1,X=0.143882,0,[53],1416.46,2.8,1,X=0.180922,0,[71],914.129,4.99,1,X=0.156587,0,[74],1230.92,23.8,1,X=0.105959,0,[93],590.277,1100.0,1,X=0.040638,0',
'10,[4],1167.96,20.0,2,K=10000.0,R=1.0,0,[7],323.965,40.0,2,K=10000.0,R=1.0,0,[26],405.824,0.011,1,X=0.722657,0,[27],270.898,0.009,1,X=0.759836,0,[28],1090.78,0.01,1,X=0.740083,0,[38],946.409,0.085,1,X=0.0181255,0,[40],462.2,0.325,1,X=0.309963,0,[49],1615.26,0.355,1,X=0.303196,0,[53],1342.79,2.8,1,X=0.180922,0,[73],351.689,17.0,1,X=0.115257,0',
'10,[3],1441.26,20.0,2,K=10000.0,R=1.0,0,[4],1036.09,20.0,2,K=10000.0,R=1.0,0,[31],326.389,0.0075,1,X=0.795271,0,[33],1736.02,0.4,1,X=0.294283,0,[42],719.45,0.205,1,X=0.34781,0,[53],1362.09,2.8,1,X=0.180922,0,[61],882.132,54.0,1,X=0.00361033,0,[72],1571.97,0.3,1,X=0.316228,0,[80],1414.5,41.5,1,X=0.0922079,0,[91],324.307,388.0,1,X=0.00220515,0',
'10,[3],453.559,20.0,2,K=10000.0,R=1.0,0,[4],1388.17,20.0,2,K=10000.0,R=1.0,0,[13],1699.25,1.15e-05,1,X=0.0365353,0,[16],1735.63,0.9,1,X=0.00218437,0,[34],271.407,0.0709,1,X=0.0189664,0,[49],592.53,0.355,1,X=0.303196,0,[50],767.207,0.349,1,X=0.304491,0,[55],991.345,0.213,1,X=0.344497,0,[67],618.636,9.6,1,X=0.132957,0,[91],1328.03,388.0,1,X=0.00220515,0',
'10,[4],838.222,20.0,2,K=10000.0,R=1.0,0,[5],1523.69,40.0,2,K=10000.0,R=1.0,0,[14],413.81,20.0,1,X=0.00100607,0,[27],1453.92,0.009,1,X=0.759836,0,[31],563.519,0.0075,1,X=0.795271,0,[47],1486.09,5.45,1,X=0.153173,0,[51],256.471,2.05,1,X=0.195588,0,[67],679.572,9.6,1,X=0.132957,0,[69],1050.87,12.5,1,X=0.124467,0,[93],936.896,1100.0,1,X=0.040638,0',
'10,[5],1321.59,40.0,2,K=10000.0,R=1.0,0,[7],1017.7,40.0,2,K=10000.0,R=1.0,0,[51],619.501,2.05,1,X=0.195588,0,[52],1678.81,7.0,1,X=0.143882,0,[67],567.897,9.6,1,X=0.132957,0,[71],1224.05,4.99,1,X=0.156587,0,[80],573.737,41.5,1,X=0.0922079,0,[85],283.399,108.0,1,X=0.072598,0,[86],1470.34,156.0,1,X=0.0662215,0,[92],1559.09,1250.0,1,X=0.0393598,0',
'10,[4],1214.46,20.0,2,K=10000.0,R=1.0,0,[5],1272.96,40.0,2,K=10000.0,R=1.0,0,[16],314.802,0.9,1,X=0.00218437,0,[33],890.731,0.4,1,X=0.294283,0,[64],252.732,10.4,1,X=0.00544988,0,[82],379.265,50.0,1,X=0.0880112,0,[86],643.403,156.0,1,X=0.0662215,0,[88],399.461,1590.0,1,X=0.0370622,0,[89],1090.76,470.0,1,X=0.0502639,0,[94],936.674,1550.0,1,X=0.037299,0',
'10,[2],360.395,20.0,2,K=10000.0,R=1.0,0,[3],1432.29,20.0,2,K=10000.0,R=1.0,0,[8],1121.64,1.1,1,X=0.00207749,0,[9],1288.69,0.071,1,X=0.00412167,0,[16],773.345,0.9,1,X=0.00218437,0,[46],1118.15,0.14,1,X=0.382603,0,[50],492.752,0.349,1,X=0.304491,0,[51],1508.49,2.05,1,X=0.195588,0,[65],644.021,13.0,1,X=0.123252,0,[85],1695.1,108.0,1,X=0.072598,0',
'10,[2],1147.41,20.0,2,K=10000.0,R=1.0,0,[4],891.572,20.0,2,K=10000.0,R=1.0,0,[14],647.513,20.0,1,X=0.00100607,0,[16],1271.8,0.9,1,X=0.00218437,0,[32],1514.48,0.13,1,X=0.0162989,0,[43],1478.31,0.03,1,X=0.562341,0,[69],767.256,12.5,1,X=0.124467,0,[73],821.127,17.0,1,X=0.115257,0,[77],838.045,38.5,1,X=0.093954,0,[80],320.993,41.5,1,X=0.0922079,0',
'10,[2],949.154,20.0,2,K=10000.0,R=1.0,0,[7],338.132,40.0,2,K=10000.0,R=1.0,0,[14],811.153,20.0,1,X=0.00100607,0,[25],268.185,0.0125,1,X=0.699927,0,[42],346.124,0.205,1,X=0.34781,0,[47],1360.42,5.45,1,X=0.153173,0,[48],1258.66,4.49,1,X=0.160775,0,[49],623.348,0.355,1,X=0.303196,0,[50],1510.51,0.349,1,X=0.304491,0,[85],971.229,108.0,1,X=0.072598,0',
'10,[5],536.535,40.0,2,K=10000.0,R=1.0,0,[7],820.637,40.0,2,K=10000.0,R=1.0,0,[14],1612.26,20.0,1,X=0.00100607,0,[29],320.216,0.035,1,X=0.541082,0,[33],508.191,0.4,1,X=0.294283,0,[49],1040.19,0.355,1,X=0.303196,0,[56],1625.59,6.25,1,X=0.148017,0,[71],256.254,4.99,1,X=0.156587,0,[74],1619.48,23.8,1,X=0.105959,0,[77],374.969,38.5,1,X=0.093954,0',
'10,[2],1555.77,20.0,2,K=10000.0,R=1.0,0,[3],1499.67,20.0,2,K=10000.0,R=1.0,0,[14],425.481,20.0,1,X=0.00100607,0,[29],1225.2,0.035,1,X=0.541082,0,[55],1316.01,0.213,1,X=0.344497,0,[57],579.34,4.2,1,X=0.163481,0,[61],831.241,54.0,1,X=0.00361033,0,[71],1397.27,4.99,1,X=0.156587,0,[72],260.449,0.3,1,X=0.316228,0,[80],1594.72,41.5,1,X=0.0922079,0',
'10,[2],614.05,20.0,2,K=10000.0,R=1.0,0,[4],550.692,20.0,2,K=10000.0,R=1.0,0,[15],1427.06,0.071,1,X=0.00412167,0,[28],1731.32,0.01,1,X=0.740083,0,[40],334.592,0.325,1,X=0.309963,0,[42],294.67,0.205,1,X=0.34781,0,[49],1184.92,0.355,1,X=0.303196,0,[55],393.921,0.213,1,X=0.344497,0,[80],363.437,41.5,1,X=0.0922079,0,[89],270.111,470.0,1,X=0.0502639,0',
'10,[3],1402.47,20.0,2,K=10000.0,R=1.0,0,[5],449.348,40.0,2,K=10000.0,R=1.0,0,[16],393.709,0.9,1,X=0.00218437,0,[31],406.334,0.0075,1,X=0.795271,0,[32],855.16,0.13,1,X=0.0162989,0,[49],367.818,0.355,1,X=0.303196,0,[50],312.38,0.349,1,X=0.304491,0,[57],1599.26,4.2,1,X=0.163481,0,[72],528.96,0.3,1,X=0.316228,0,[86],286.668,156.0,1,X=0.0662215,0',
'10,[4],1456.17,20.0,2,K=10000.0,R=1.0,0,[7],1607.17,40.0,2,K=10000.0,R=1.0,0,[26],268.444,0.011,1,X=0.722657,0,[31],292.806,0.0075,1,X=0.795271,0,[38],294.907,0.085,1,X=0.0181255,0,[43],1563.43,0.03,1,X=0.562341,0,[46],947.329,0.14,1,X=0.382603,0,[49],1409.5,0.355,1,X=0.303196,0,[50],1205.66,0.349,1,X=0.304491,0,[69],1594.6,12.5,1,X=0.124467,0',
'10,[4],750.368,20.0,2,K=10000.0,R=1.0,0,[5],1746.18,40.0,2,K=10000.0,R=1.0,0,[26],1733.57,0.011,1,X=0.722657,0,[33],1176.19,0.4,1,X=0.294283,0,[43],1238.95,0.03,1,X=0.562341,0,[49],876.778,0.355,1,X=0.303196,0,[69],1529.19,12.5,1,X=0.124467,0,[73],439.091,17.0,1,X=0.115257,0,[80],486.543,41.5,1,X=0.0922079,0,[89],1527.06,470.0,1,X=0.0502639,0',
'10,[4],639.739,20.0,2,K=10000.0,R=1.0,0,[5],955.747,40.0,2,K=10000.0,R=1.0,0,[27],687.762,0.009,1,X=0.759836,0,[44],261.502,0.028,1,X=0.0239252,0,[49],1182.28,0.355,1,X=0.303196,0,[51],1016.71,2.05,1,X=0.195588,0,[63],1749.37,7.85,1,X=0.139818,0,[73],1019.11,17.0,1,X=0.115257,0,[80],320.9,41.5,1,X=0.0922079,0,[89],787.019,470.0,1,X=0.0502639,0',
'10,[3],1497.79,20.0,2,K=10000.0,R=1.0,0,[7],361.355,40.0,2,K=10000.0,R=1.0,0,[28],409.084,0.01,1,X=0.740083,0,[33],832.734,0.4,1,X=0.294283,0,[44],316.728,0.028,1,X=0.0239252,0,[51],1138.32,2.05,1,X=0.195588,0,[73],332.408,17.0,1,X=0.115257,0,[83],692.531,103.0,1,X=0.0734634,0,[85],463.05,108.0,1,X=0.072598,0,[86],1302.56,156.0,1,X=0.0662215,0',
'10,[3],1525.7,20.0,2,K=10000.0,R=1.0,0,[4],1488.37,20.0,2,K=10000.0,R=1.0,0,[30],1697.63,0.029,1,X=0.567128,0,[31],1345.75,0.0075,1,X=0.795271,0,[49],750.75,0.355,1,X=0.303196,0,[50],826.7,0.349,1,X=0.304491,0,[64],939.35,10.4,1,X=0.00544988,0,[82],260.733,50.0,1,X=0.0880112,0,[83],439.643,103.0,1,X=0.0734634,0,[86],594.205,156.0,1,X=0.0662215,0',
'10,[4],709.52,20.0,2,K=10000.0,R=1.0,0,[5],803.428,40.0,2,K=10000.0,R=1.0,0,[31],1689.83,0.0075,1,X=0.795271,0,[47],887.818,5.45,1,X=0.153173,0,[49],675.133,0.355,1,X=0.303196,0,[50],1254.91,0.349,1,X=0.304491,0,[69],1160.26,12.5,1,X=0.124467,0,[72],1099.53,0.3,1,X=0.316228,0,[73],1476.21,17.0,1,X=0.115257,0,[74],259.493,23.8,1,X=0.105959,0',
'10,[5],718.713,40.0,2,K=10000.0,R=1.0,0,[7],1380.39,40.0,2,K=10000.0,R=1.0,0,[42],1590.27,0.205,1,X=0.34781,0,[61],1122.55,54.0,1,X=0.00361033,0,[73],1391.5,17.0,1,X=0.115257,0,[80],375.049,41.5,1,X=0.0922079,0,[82],494.005,50.0,1,X=0.0880112,0,[89],1013.24,470.0,1,X=0.0502639,0,[91],410.44,388.0,1,X=0.00220515,0,[94],1266.39,1550.0,1,X=0.037299,0',
'15,[3],671.378,20.0,2,K=10000.0,R=1.0,0,[5],520.907,40.0,2,K=10000.0,R=1.0,0,[7],1459.58,40.0,2,K=10000.0,R=1.0,0,[14],557.127,20.0,1,X=0.00100607,0,[18],1268.04,0.00014,1,X=0.0195594,0,[21],485.232,0.2,1,X=0.00318149,0,[28],670.427,0.01,1,X=0.740083,0,[45],407.138,0.425,1,X=0.289857,0,[49],1666.4,0.355,1,X=0.303196,0,[50],297.512,0.349,1,X=0.304491,0,[55],704.989,0.213,1,X=0.344497,0,[67],1299.86,9.6,1,X=0.132957,0,[70],1705.03,13.0,1,X=0.123252,0,[93],293.132,1100.0,1,X=0.040638,0,[95],905.91,5520.0,1,X=0.0271516,0',
'15,[3],713.893,20.0,2,K=10000.0,R=1.0,0,[5],1488.21,40.0,2,K=10000.0,R=1.0,0,[7],541.833,40.0,2,K=10000.0,R=1.0,0,[13],802.607,1.15e-05,1,X=0.0365353,0,[27],385.923,0.009,1,X=0.759836,0,[31],643.961,0.0075,1,X=0.795271,0,[34],352.117,0.0709,1,X=0.0189664,0,[38],252.303,0.085,1,X=0.0181255,0,[42],1625.46,0.205,1,X=0.34781,0,[51],950.508,2.05,1,X=0.195588,0,[63],1517.28,7.85,1,X=0.139818,0,[66],1121.96,10.2,1,X=0.130957,0,[70],1470.44,13.0,1,X=0.123252,0,[74],603.148,23.8,1,X=0.105959,0,[75],1441.58,1.59,1,X=0.00871558,0',
'15,[2],1305.73,20.0,2,K=10000.0,R=1.0,0,[4],976.7,20.0,2,K=10000.0,R=1.0,0,[5],743.221,40.0,2,K=10000.0,R=1.0,0,[16],1349.73,0.9,1,X=0.00218437,0,[42],1415.24,0.205,1,X=0.34781,0,[55],1551.03,0.213,1,X=0.344497,0,[57],1514.24,4.2,1,X=0.163481,0,[61],1115.04,54.0,1,X=0.00361033,0,[64],252.55,10.4,1,X=0.00544988,0,[70],367.16,13.0,1,X=0.123252,0,[85],252.282,108.0,1,X=0.072598,0,[86],1230.73,156.0,1,X=0.0662215,0,[88],880.931,1590.0,1,X=0.0370622,0,[89],506.964,470.0,1,X=0.0502639,0,[91],1640.38,388.0,1,X=0.00220515,0',
'15,[4],1148.1,20.0,2,K=10000.0,R=1.0,0,[5],578.785,40.0,2,K=10000.0,R=1.0,0,[7],830.566,40.0,2,K=10000.0,R=1.0,0,[26],1233.16,0.011,1,X=0.722657,0,[42],270.675,0.205,1,X=0.34781,0,[45],1206.98,0.425,1,X=0.289857,0,[49],268.001,0.355,1,X=0.303196,0,[55],916.348,0.213,1,X=0.344497,0,[66],1067.12,10.2,1,X=0.130957,0,[70],1722.97,13.0,1,X=0.123252,0,[86],270.344,156.0,1,X=0.0662215,0,[88],763.826,1590.0,1,X=0.0370622,0,[89],1031.4,470.0,1,X=0.0502639,0,[91],598.407,388.0,1,X=0.00220515,0,[93],969.536,1100.0,1,X=0.040638,0',
'15,[2],260.973,20.0,2,K=10000.0,R=1.0,0,[5],1274.61,40.0,2,K=10000.0,R=1.0,0,[7],586.107,40.0,2,K=10000.0,R=1.0,0,[14],542.146,20.0,1,X=0.00100607,0,[31],1507.56,0.0075,1,X=0.795271,0,[33],1102.08,0.4,1,X=0.294283,0,[36],785.25,3.5,1,X=0.00715531,0,[49],820.551,0.355,1,X=0.303196,0,[50],960.535,0.349,1,X=0.304491,0,[64],291.694,10.4,1,X=0.00544988,0,[69],1382.14,12.5,1,X=0.124467,0,[70],1003.34,13.0,1,X=0.123252,0,[80],1388.41,41.5,1,X=0.0922079,0,[85],652.129,108.0,1,X=0.072598,0,[91],397.176,388.0,1,X=0.00220515,0',
'15,[2],569.509,20.0,2,K=10000.0,R=1.0,0,[3],392.91,20.0,2,K=10000.0,R=1.0,0,[4],471.15,20.0,2,K=10000.0,R=1.0,0,[9],1603.17,0.071,1,X=0.00412167,0,[15],256.778,0.071,1,X=0.00412167,0,[21],1137.36,0.2,1,X=0.00318149,0,[28],905.031,0.01,1,X=0.740083,0,[51],1552.32,2.05,1,X=0.195588,0,[53],844.175,2.8,1,X=0.180922,0,[57],736.182,4.2,1,X=0.163481,0,[61],890.41,54.0,1,X=0.00361033,0,[72],761.245,0.3,1,X=0.316228,0,[73],1370.72,17.0,1,X=0.115257,0,[74],1618.75,23.8,1,X=0.105959,0,[75],501.304,1.59,1,X=0.00871558,0',
'15,[3],1187.39,20.0,2,K=10000.0,R=1.0,0,[5],953.67,40.0,2,K=10000.0,R=1.0,0,[7],1606.64,40.0,2,K=10000.0,R=1.0,0,[13],1049.43,1.15e-05,1,X=0.0365353,0,[23],1448.2,0.003,1,X=1.0,0,[30],747.019,0.029,1,X=0.567128,0,[31],505.885,0.0075,1,X=0.795271,0,[34],1476.91,0.0709,1,X=0.0189664,0,[42],837.881,0.205,1,X=0.34781,0,[49],1155.34,0.355,1,X=0.303196,0,[50],1236.47,0.349,1,X=0.304491,0,[53],1305.64,2.8,1,X=0.180922,0,[57],1595.19,4.2,1,X=0.163481,0,[80],1398.61,41.5,1,X=0.0922079,0,[95],777.594,5520.0,1,X=0.0271516,0',
'15,[2],1102.24,20.0,2,K=10000.0,R=1.0,0,[3],1517.55,20.0,2,K=10000.0,R=1.0,0,[4],1351.23,20.0,2,K=10000.0,R=1.0,0,[14],1570.98,20.0,1,X=0.00100607,0,[25],1652.27,0.0125,1,X=0.699927,0,[40],1147.11,0.325,1,X=0.309963,0,[42],1498.36,0.205,1,X=0.34781,0,[49],1052.49,0.355,1,X=0.303196,0,[50],1404.39,0.349,1,X=0.304491,0,[53],1468.94,2.8,1,X=0.180922,0,[72],398.975,0.3,1,X=0.316228,0,[74],1647.44,23.8,1,X=0.105959,0,[83],1116.92,103.0,1,X=0.0734634,0,[85],259.577,108.0,1,X=0.072598,0,[86],572.998,156.0,1,X=0.0662215,0',
'15,[3],1051.19,20.0,2,K=10000.0,R=1.0,0,[4],528.603,20.0,2,K=10000.0,R=1.0,0,[5],394.344,40.0,2,K=10000.0,R=1.0,0,[47],1276.04,5.45,1,X=0.153173,0,[59],723.195,3.35,1,X=0.172989,0,[66],683.777,10.2,1,X=0.130957,0,[69],358.59,12.5,1,X=0.124467,0,[71],865.929,4.99,1,X=0.156587,0,[75],320.566,1.59,1,X=0.00871558,0,[80],322.079,41.5,1,X=0.0922079,0,[82],747.049,50.0,1,X=0.0880112,0,[83],1632.43,103.0,1,X=0.0734634,0,[86],1025.79,156.0,1,X=0.0662215,0,[89],1276.38,470.0,1,X=0.0502639,0,[94],1116.04,1550.0,1,X=0.037299,0',
'15,[2],1675.64,20.0,2,K=10000.0,R=1.0,0,[3],1146.51,20.0,2,K=10000.0,R=1.0,0,[7],1381.87,40.0,2,K=10000.0,R=1.0,0,[15],303.7,0.071,1,X=0.00412167,0,[24],452.849,0.005,1,X=0.00800102,0,[29],252.208,0.035,1,X=0.541082,0,[31],1656.89,0.0075,1,X=0.795271,0,[59],1322.19,3.35,1,X=0.172989,0,[65],460.195,13.0,1,X=0.123252,0,[72],993.604,0.3,1,X=0.316228,0,[77],467.518,38.5,1,X=0.093954,0,[80],1091.78,41.5,1,X=0.0922079,0,[85],1645.02,108.0,1,X=0.072598,0,[89],558.324,470.0,1,X=0.0502639,0,[91],352.435,388.0,1,X=0.00220515,0',
'15,[4],673.523,20.0,2,K=10000.0,R=1.0,0,[5],321.946,40.0,2,K=10000.0,R=1.0,0,[7],329.283,40.0,2,K=10000.0,R=1.0,0,[27],1483.81,0.009,1,X=0.759836,0,[28],280.402,0.01,1,X=0.740083,0,[45],1499.11,0.425,1,X=0.289857,0,[48],1227.19,4.49,1,X=0.160775,0,[49],361.113,0.355,1,X=0.303196,0,[57],382.873,4.2,1,X=0.163481,0,[67],1109.13,9.6,1,X=0.132957,0,[75],1733.75,1.59,1,X=0.00871558,0,[85],265.638,108.0,1,X=0.072598,0,[86],784.387,156.0,1,X=0.0662215,0,[89],750.398,470.0,1,X=0.0502639,0,[92],1442.45,1250.0,1,X=0.0393598,0',
'15,[2],604.05,20.0,2,K=10000.0,R=1.0,0,[4],305.666,20.0,2,K=10000.0,R=1.0,0,[5],602.831,40.0,2,K=10000.0,R=1.0,0,[31],289.535,0.0075,1,X=0.795271,0,[45],1107.52,0.425,1,X=0.289857,0,[51],1614.74,2.05,1,X=0.195588,0,[52],1255.7,7.0,1,X=0.143882,0,[55],993.714,0.213,1,X=0.344497,0,[57],778.254,4.2,1,X=0.163481,0,[61],536.673,54.0,1,X=0.00361033,0,[67],1427.44,9.6,1,X=0.132957,0,[75],1712.21,1.59,1,X=0.00871558,0,[93],866.96,1100.0,1,X=0.040638,0,[94],1599.91,1550.0,1,X=0.037299,0,[95],274.473,5520.0,1,X=0.0271516,0',
'15,[2],897.706,20.0,2,K=10000.0,R=1.0,0,[5],1435.55,40.0,2,K=10000.0,R=1.0,0,[7],1028.07,40.0,2,K=10000.0,R=1.0,0,[8],858.053,1.1,1,X=0.00207749,0,[9],616.524,0.071,1,X=0.00412167,0,[11],824.168,4e-06,1,X=0.0475743,0,[36],278.942,3.5,1,X=0.00715531,0,[39],781.217,0.085,1,X=0.433437,0,[48],1539.01,4.49,1,X=0.160775,0,[61],857.541,54.0,1,X=0.00361033,0,[67],930.374,9.6,1,X=0.132957,0,[73],1087.38,17.0,1,X=0.115257,0,[80],414.652,41.5,1,X=0.0922079,0,[85],363.947,108.0,1,X=0.072598,0,[91],1644.58,388.0,1,X=0.00220515,0',
'15,[2],1536.9,20.0,2,K=10000.0,R=1.0,0,[4],509.723,20.0,2,K=10000.0,R=1.0,0,[7],815.839,40.0,2,K=10000.0,R=1.0,0,[16],1019.86,0.9,1,X=0.00218437,0,[28],273.861,0.01,1,X=0.740083,0,[47],697.027,5.45,1,X=0.153173,0,[49],1624.76,0.355,1,X=0.303196,0,[52],788.967,7.0,1,X=0.143882,0,[55],723.221,0.213,1,X=0.344497,0,[61],1149.41,54.0,1,X=0.00361033,0,[63],1476.88,7.85,1,X=0.139818,0,[64],421.845,10.4,1,X=0.00544988,0,[67],1233.24,9.6,1,X=0.132957,0,[83],1425.28,103.0,1,X=0.0734634,0,[86],1045.86,156.0,1,X=0.0662215,0',
'15,[4],1489.21,20.0,2,K=10000.0,R=1.0,0,[5],856.863,40.0,2,K=10000.0,R=1.0,0,[7],1070.51,40.0,2,K=10000.0,R=1.0,0,[16],295.769,0.9,1,X=0.00218437,0,[27],781.154,0.009,1,X=0.759836,0,[31],652.568,0.0075,1,X=0.795271,0,[40],538.687,0.325,1,X=0.309963,0,[49],367.177,0.355,1,X=0.303196,0,[63],1259.7,7.85,1,X=0.139818,0,[64],712.51,10.4,1,X=0.00544988,0,[71],635.851,4.99,1,X=0.156587,0,[73],767.948,17.0,1,X=0.115257,0,[75],1342.43,1.59,1,X=0.00871558,0,[77],500.275,38.5,1,X=0.093954,0,[80],638.528,41.5,1,X=0.0922079,0',
'15,[2],1361.14,20.0,2,K=10000.0,R=1.0,0,[3],546.652,20.0,2,K=10000.0,R=1.0,0,[5],294.306,40.0,2,K=10000.0,R=1.0,0,[13],573.803,1.15e-05,1,X=0.0365353,0,[20],1531.31,0.04,1,X=0.0218842,0,[29],304.697,0.035,1,X=0.541082,0,[30],431.676,0.029,1,X=0.567128,0,[49],264.092,0.355,1,X=0.303196,0,[50],799.004,0.349,1,X=0.304491,0,[52],974.353,7.0,1,X=0.143882,0,[55],1095.35,0.213,1,X=0.344497,0,[65],1265.11,13.0,1,X=0.123252,0,[82],1262.42,50.0,1,X=0.0880112,0,[86],1061.8,156.0,1,X=0.0662215,0,[88],750.42,1590.0,1,X=0.0370622,0',
'15,[2],459.194,20.0,2,K=10000.0,R=1.0,0,[4],439.107,20.0,2,K=10000.0,R=1.0,0,[5],603.729,40.0,2,K=10000.0,R=1.0,0,[8],585.546,1.1,1,X=0.00207749,0,[9],1397.82,0.071,1,X=0.00412167,0,[10],326.461,0.004,1,X=0.00846004,0,[14],1584.58,20.0,1,X=0.00100607,0,[17],934.85,0.17,1,X=0.00331341,0,[55],698.303,0.213,1,X=0.344497,0,[71],440.645,4.99,1,X=0.156587,0,[86],1148.9,156.0,1,X=0.0662215,0,[87],508.172,112.0,1,X=0.0719409,0,[91],1629.56,388.0,1,X=0.00220515,0,[94],1302.72,1550.0,1,X=0.037299,0,[95],317.331,5520.0,1,X=0.0271516,0',
'15,[2],369.906,20.0,2,K=10000.0,R=1.0,0,[4],636.708,20.0,2,K=10000.0,R=1.0,0,[7],718.355,40.0,2,K=10000.0,R=1.0,0,[11],408.909,4e-06,1,X=0.0475743,0,[34],1729.47,0.0709,1,X=0.0189664,0,[36],450.135,3.5,1,X=0.00715531,0,[40],1665.49,0.325,1,X=0.309963,0,[49],353.333,0.355,1,X=0.303196,0,[50],1181.73,0.349,1,X=0.304491,0,[55],446.421,0.213,1,X=0.344497,0,[71],934.869,4.99,1,X=0.156587,0,[72],1076.35,0.3,1,X=0.316228,0,[80],1592.0,41.5,1,X=0.0922079,0,[87],613.972,112.0,1,X=0.0719409,0,[95],1673.95,5520.0,1,X=0.0271516,0',
'15,[3],1331.15,20.0,2,K=10000.0,R=1.0,0,[5],327.19,40.0,2,K=10000.0,R=1.0,0,[7],768.165,40.0,2,K=10000.0,R=1.0,0,[13],597.641,1.15e-05,1,X=0.0365353,0,[21],1365.52,0.2,1,X=0.00318149,0,[25],1129.43,0.0125,1,X=0.699927,0,[26],1360.11,0.011,1,X=0.722657,0,[41],458.831,0.287,1,X=0.319749,0,[52],530.536,7.0,1,X=0.143882,0,[55],758.131,0.213,1,X=0.344497,0,[63],1580.84,7.85,1,X=0.139818,0,[74],648.534,23.8,1,X=0.105959,0,[80],1607.9,41.5,1,X=0.0922079,0,[85],1295.41,108.0,1,X=0.072598,0,[91],251.251,388.0,1,X=0.00220515,0',
'15,[2],796.593,20.0,2,K=10000.0,R=1.0,0,[5],502.671,40.0,2,K=10000.0,R=1.0,0,[7],530.25,40.0,2,K=10000.0,R=1.0,0,[14],731.708,20.0,1,X=0.00100607,0,[17],405.294,0.17,1,X=0.00331341,0,[29],1384.73,0.035,1,X=0.541082,0,[36],1066.31,3.5,1,X=0.00715531,0,[49],434.73,0.355,1,X=0.303196,0,[50],743.968,0.349,1,X=0.304491,0,[52],252.062,7.0,1,X=0.143882,0,[55],1432.38,0.213,1,X=0.344497,0,[80],514.141,41.5,1,X=0.0922079,0,[93],1707.84,1100.0,1,X=0.040638,0,[94],780.177,1550.0,1,X=0.037299,0,[95],930.189,5520.0,1,X=0.0271516,0',
'15,[3],1057.63,20.0,2,K=10000.0,R=1.0,0,[4],905.011,20.0,2,K=10000.0,R=1.0,0,[7],1413.88,40.0,2,K=10000.0,R=1.0,0,[14],854.22,20.0,1,X=0.00100607,0,[21],1143.54,0.2,1,X=0.00318149,0,[26],293.588,0.011,1,X=0.722657,0,[44],269.445,0.028,1,X=0.0239252,0,[48],1053.45,4.49,1,X=0.160775,0,[55],681.108,0.213,1,X=0.344497,0,[65],938.292,13.0,1,X=0.123252,0,[80],1292.24,41.5,1,X=0.0922079,0,[85],662.612,108.0,1,X=0.072598,0,[86],976.77,156.0,1,X=0.0662215,0,[89],1043.27,470.0,1,X=0.0502639,0,[93],1652.87,1100.0,1,X=0.040638,0',
'15,[2],1132.96,20.0,2,K=10000.0,R=1.0,0,[4],1101.68,20.0,2,K=10000.0,R=1.0,0,[5],803.609,40.0,2,K=10000.0,R=1.0,0,[14],765.515,20.0,1,X=0.00100607,0,[27],1525.52,0.009,1,X=0.759836,0,[33],329.648,0.4,1,X=0.294283,0,[41],395.719,0.287,1,X=0.319749,0,[44],1059.56,0.028,1,X=0.0239252,0,[56],1748.37,6.25,1,X=0.148017,0,[61],252.195,54.0,1,X=0.00361033,0,[64],271.897,10.4,1,X=0.00544988,0,[82],1748.91,50.0,1,X=0.0880112,0,[83],1167.62,103.0,1,X=0.0734634,0,[86],379.827,156.0,1,X=0.0662215,0,[91],789.379,388.0,1,X=0.00220515,0',
'15,[2],797.96,20.0,2,K=10000.0,R=1.0,0,[4],612.258,20.0,2,K=10000.0,R=1.0,0,[5],1245.21,40.0,2,K=10000.0,R=1.0,0,[15],1345.29,0.071,1,X=0.00412167,0,[16],910.555,0.9,1,X=0.00218437,0,[27],462.903,0.009,1,X=0.759836,0,[29],346.148,0.035,1,X=0.541082,0,[38],261.639,0.085,1,X=0.0181255,0,[55],1012.21,0.213,1,X=0.344497,0,[61],334.691,54.0,1,X=0.00361033,0,[80],594.253,41.5,1,X=0.0922079,0,[83],733.392,103.0,1,X=0.0734634,0,[85],918.244,108.0,1,X=0.072598,0,[86],1668.23,156.0,1,X=0.0662215,0,[95],526.371,5520.0,1,X=0.0271516,0',
'15,[3],623.816,20.0,2,K=10000.0,R=1.0,0,[4],250.636,20.0,2,K=10000.0,R=1.0,0,[5],1516.31,40.0,2,K=10000.0,R=1.0,0,[26],808.706,0.011,1,X=0.722657,0,[27],1033.14,0.009,1,X=0.759836,0,[31],770.598,0.0075,1,X=0.795271,0,[38],495.947,0.085,1,X=0.0181255,0,[43],1307.29,0.03,1,X=0.562341,0,[44],283.639,0.028,1,X=0.0239252,0,[47],787.553,5.45,1,X=0.153173,0,[69],402.203,12.5,1,X=0.124467,0,[71],1652.2,4.99,1,X=0.156587,0,[86],1304.6,156.0,1,X=0.0662215,0,[87],809.114,112.0,1,X=0.0719409,0,[95],1728.82,5520.0,1,X=0.0271516,0',
'15,[4],353.861,20.0,2,K=10000.0,R=1.0,0,[5],572.332,40.0,2,K=10000.0,R=1.0,0,[7],1243.75,40.0,2,K=10000.0,R=1.0,0,[31],985.872,0.0075,1,X=0.795271,0,[41],279.781,0.287,1,X=0.319749,0,[46],1298.59,0.14,1,X=0.382603,0,[49],359.851,0.355,1,X=0.303196,0,[50],901.043,0.349,1,X=0.304491,0,[56],886.969,6.25,1,X=0.148017,0,[64],668.864,10.4,1,X=0.00544988,0,[83],822.255,103.0,1,X=0.0734634,0,[86],414.755,156.0,1,X=0.0662215,0,[89],1017.0,470.0,1,X=0.0502639,0,[92],350.476,1250.0,1,X=0.0393598,0,[95],1391.09,5520.0,1,X=0.0271516,0'
]

assert len(node_configs) == 75

for set_num, node_config in enumerate(node_configs, start=177):
    generator_functions[set_num] = lambda nc=node_config: vary_x_k(nc)

assert max(generator_functions.keys()) == 251

# 20-species initialBiomass variations
generator_functions[253] = lambda: vary_initial_biomass([2, 3, 4, 5, 14, 15, 16, 31, 34, 39, 41, 42, 53, 57, 65, 80, 82, 83, 85, 86])
generator_functions[254] = lambda: vary_initial_biomass([2, 3, 4, 5, 8, 9, 16, 27, 29, 30, 38, 49, 50, 59, 66, 75, 83, 86, 87, 93])
generator_functions[255] = lambda: vary_initial_biomass([2, 3, 4, 7, 9, 13, 15, 26, 27, 44, 48, 49, 52, 61, 66, 67, 73, 80, 86, 89])
generator_functions[256] = lambda: vary_initial_biomass([2, 3, 4, 5, 26, 27, 30, 33, 49, 50, 55, 59, 69, 82, 83, 86, 87, 88, 93, 95])
generator_functions[257] = lambda: vary_initial_biomass([2, 3, 4, 7, 8, 9, 11, 20, 30, 33, 36, 47, 49, 50, 61, 67, 74, 75, 79, 85])
