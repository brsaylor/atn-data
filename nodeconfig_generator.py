#!/usr/bin/env python3

# Ben Saylor
# October 2015

import sys
from copy import copy, deepcopy
import random
import re
import itertools
import bisect

import util

from weka_em import parse_weka_em_output

# Functions that generate and print out node configs, keyed by set number.
generatorFunctions = {}

# Parameter sliders in Convergence game are bounded by these ranges
validParamRanges = {
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
convergenceNodeConfigs = [
    '5,[5],2000.0,1.0,1,K=10000.000,0,[14],1751.0,20.0,1,X=0.201,0,[31],1415.0,0.0075,1,X=1.000,0,[42],240.0,0.205,1,X=0.637,0,[70],2494.0,13.0,1,X=0.155,0',

    '6,[5],2000,1.000,1,K=8000.000,0,[14],1051,20.000,1,X=0.200,0,[31],29,0.008,1,X=0.950,0,[33],2476,0.400,1,X=0.370,0,[56],738,6.250,1,X=0.180,0,[59],674,3.350,1,X=0.220,0',

    '11,[2],433,528.000,2,R=2.000,K=3000.000,0,[3],433,528.000,1,K=3000.000,0,[4],433,528.000,1,K=3000.000,0,[5],2000,1.000,1,K=4000.000,0,[7],668,816.000,1,K=3000.000,0,[49],1308,0.355,1,X=0.870,0,[55],576,0.213,1,X=0.990,0,[61],601,54.000,1,X=0.010,0,[74],725,50.000,1,X=0.100,0,[82],700,50.000,1,X=0.750,0,[83],300,103.000,1,X=0.210,0',

    '15,[1],400,1.000,1,K=2000.000,0,[2],1056,20.000,1,K=3000.000,0,[5],2000,1.000,1,K=7000.000,0,[7],1322,40.000,1,K=3000.000,0,[9],1913,0.071,1,X=0.310,0,[12],300,1.000,0,0,[26],1164,0.011,1,X=1.000,0,[45],916,0.425,1,X=0.400,0,[49],1015,0.355,1,X=0.300,0,[55],1849,0.310,1,X=0.480,0,[67],1434,9.600,1,X=0.340,0,[71],564,4.990,1,X=0.270,0,[75],568,1.590,1,X=0.010,0,[80],575,41.500,1,X=0.220,0,[87],240,112.000,1,X=0.100,0',

    '17,[1],2000,1000.000,2,K=3000.000,X=0.052,0,[2],657,528.000,1,K=3000.000,0,[3],657,528.000,1,K=3000.000,0,[4],657,528.000,1,K=3000.000,0,[5],2000,1.000,1,K=5000.000,0,[7],1015,816.000,1,K=3000.000,0,[19],211,20.000,1,X=0.100,0,[21],400,0.200,1,X=0.200,0,[26],496,0.011,1,X=0.910,0,[29],964,0.035,1,X=0.680,0,[31],700,0.008,1,X=1.000,0,[35],1000,250.000,1,X=0.070,0,[36],1322,3.500,1,X=0.010,0,[39],1178,0.085,1,X=0.540,0,[56],1281,6.250,1,X=0.090,0,[66],203,10.200,1,X=0.160,0,[80],719,41.500,1,X=0.120,0',
    ]

def parseNodeConfig(nodeConfig):
    """
    Parse a node config string and return a list-of-dicts representation.
    """
    nodes = []
    configList = nodeConfig.split(',')
    numNodes = int(configList[0])

    pos = 1  # current position in the comma-split list

    for i in range(numNodes):
        node = {
                'nodeId': int(configList[pos][1:-1]),  # FIXME validate [#]
                'initialBiomass': float(configList[pos+1]),
                'perUnitBiomass': float(configList[pos+2]),
                }
        numParams = int(configList[pos+3])
        pos += 4
        for p in range(numParams):
            paramName, paramValue = configList[pos].split('=')
            node[paramName] = float(paramValue)
            pos += 1
        pos += 1  # FIXME assuming there are no node link parameters
        nodes.append(node)

    return nodes

def generateNodeConfig(nodes):
    """
    Convert a list-of-dicts representation of a node config into a string.
    """

    nodeConfig = str(len(nodes))
    for node in nodes:
        nodeConfig += (',[{nodeId}],{initialBiomass:.6},{perUnitBiomass},'
                .format(**node))

        paramCount = 0
        paramConfig = ''
        for param in ('K', 'R', 'X'):
            if param in node:
                paramConfig += '{}={:.6},'.format(param, float(node[param]))
                paramCount += 1

        # The final 0 is for the number of link parameters, which is always 0
        nodeConfig += '{},{}0'.format(paramCount, paramConfig)

    return nodeConfig

# Change from Convergence 5-species template: addition of R for the grass.
# Inspection of WoB_Server code (SimJob) reveals that R defaults to 1.0.

testNodeConfig = '5,[5],2000.0,1.0,2,K=10000.0,R=1.0,0,[14],1751.0,20.0,1,X=0.201,0,[31],1415.0,0.0075,1,X=1.0,0,[42],240.0,0.205,1,X=0.637,0,[70],2494.0,13.0,1,X=0.155,0'

testNodes = [
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
assert(parseNodeConfig(testNodeConfig) == testNodes)
assert(generateNodeConfig(testNodes) == testNodeConfig)

def generateSet1():
    """
    Vary one node at a time, one parameter at a time, based on the 5-species
    ecosystem from the Convergence game. Parameters are varied in a +/- 50%
    range in 5% increments.
    """

    templateNodes = testNodes
    nodes = deepcopy(templateNodes)

    # Print unaltered nodeconfig first
    print(generateNodeConfig(nodes))

    # Change one node at a time
    for i in range(len(nodes)):

        # Vary one parameter at a time, +/- 50% in 5% increments
        for param in ('initialBiomass', 'K', 'R', 'X'):
            if param in nodes[i]:
                for percent in range(50, 151, 5):

                    # Don't print the original nodeconfig again
                    if percent == 100:
                        continue

                    nodes[i][param] = testNodes[i][param] * percent / 100
                    print(generateNodeConfig(nodes))
                nodes[i] = copy(testNodes[i])  # reset the node

# FIXME: Print unaltered nodeconfig first, skip in loop
def generatePairVariations(templateNodes, param,
        minPercent, maxPercent, stepPercent, startPos=0):
    """
    For each pair of nodes in 'templateNodes' with parameter 'param', print node
    configs with all combinations of values for 'param' within the given
    percentage range.

    The startPos parameter is the node index at which to start the procedure
    (nodes before this position are not varied).
    """

    nodes = deepcopy(templateNodes)

    for i in range(startPos, len(nodes) - 1):
        if param not in nodes[i]:
            continue
        for j in range(i + 1, len(nodes)):
            if param not in nodes[j]:
                continue

            # Now, two nodes i and j are selected.
            # Generate all combinations of values of 'param' for i and j
            for percent_i in range(minPercent, maxPercent + 1, stepPercent):
                nodes[i][param] = templateNodes[i][param] * percent_i / 100
                for percent_j in range(minPercent, maxPercent + 1, stepPercent):
                    nodes[j][param] = templateNodes[j][param] * percent_j / 100
                    print(generateNodeConfig(nodes))

            nodes[j] = copy(templateNodes[j])  # reset node j
        nodes[i] = copy(templateNodes[i])  # reset node i

def generateTripleVariations(templateNodes, param,
        minPercent, maxPercent, stepPercent):
    """
    Like generatePairVariations, but with every combination of three nodes that
    have parameter 'param'.
    """

    nodes = deepcopy(templateNodes)

    for k in range(len(nodes) - 2):
        if param not in nodes[k]:
            continue
        for percent in range(minPercent, maxPercent + 1, stepPercent):
            nodes[k][param] = templateNodes[k][param] + percent / 100
            generatePairVariations(nodes, param,
                    minPercent, maxPercent, stepPercent, startPos=k+1)
        nodes[k] = copy(templateNodes[k])  # reset node k

def generateSet2():
    """
    Base config: testNodes
    For each pair of nodes with an X parameter, generate configs with all
    combinations of X values ranging between +/- 50% of the original value, in
    10% increments.
    """
    generatePairVariations(testNodes, 'X', 50, 150, 10)

def generateSet3():
    """
    Base config: testNodes
    """
    generateTripleVariations(testNodes, 'X', 50, 150, 10)

def generateSet4():
    """
    Base config: testNodes
    Try various combinations of K and R for the grass, and for each combination,
    vary X of each other node.
    """
    nodes = deepcopy(testNodes)
    for percentK in range(50, 151, 10):
        nodes[0]['K'] = testNodes[0]['K'] * percentK / 100
        for percentR in range(50, 151, 10):
            nodes[0]['R'] = testNodes[0]['R'] * percentR / 100
            for i in range(1, len(nodes)):
                for percentX in range(50, 151, 10):
                    nodes[i]['X'] = testNodes[i]['X'] * percentX / 100
                    print(generateNodeConfig(nodes))
                nodes[i] = copy(testNodes[i])  # reset node i

convergeEcosystem3NodeConfig = '11,[2],433,528.000,2,R=2.000,K=3000.000,0,[3],433,528.000,1,K=3000.000,0,[4],433,528.000,1,K=3000.000,0,[5],2000,1.000,1,K=4000.000,0,[7],668,816.000,1,K=3000.000,0,[49],1308,0.355,1,X=0.870,0,[55],576,0.213,1,X=0.990,0,[61],601,54.000,1,X=0.010,0,[74],725,50.000,1,X=0.100,0,[82],700,50.000,1,X=0.750,0,[83],300,103.000,1,X=0.210,0'

convergeEcosystem3Nodes = parseNodeConfig(convergeEcosystem3NodeConfig)

def generateAllParamSingleVariations(templateNodes,
        minPercent, maxPercent, stepPercent):
    """
    (Similar to generateSet1) Vary one node at a time, one parameter at a time,
    based on templateNodes.  Parameters are varied in from minPercent to
    maxPercent in stepPercent increments.
    """

    # Write the unaltered nodeconfig first
    print(generateNodeConfig(templateNodes))

    nodes = deepcopy(templateNodes)

    # Change one node at a time
    for i in range(len(nodes)):

        # Vary one parameter at a time, +/- 50% in 5% increments
        for param in ('initialBiomass', 'K', 'R', 'X'):
            if param in nodes[i]:
                for percent in range(minPercent, maxPercent + 1, stepPercent):

                    # Don't print the original nodeconfig again
                    if percent == 100:
                        continue

                    nodes[i][param] = templateNodes[i][param] * percent / 100
                    print(generateNodeConfig(nodes))
                nodes[i] = copy(templateNodes[i])  # reset the node

def generateRandomVariations(templateNodes,
        params, minPercent, maxPercent, count):
    """
    Generate <count> random variations of parameter values on all nodes,
    for parameters named in <params>.
    """
    minRatio = minPercent / 100
    maxRatio = maxPercent / 100
    params = set(params)

    # Write the unaltered nodeconfig first
    print(generateNodeConfig(templateNodes))

    nodes = deepcopy(templateNodes)
    for i in range(count - 1):
        for j, node in enumerate(nodes):
            for param in node.keys():
                if param in params:
                    node[param] = (templateNodes[j][param] *
                            random.uniform(minRatio, maxRatio))
                    # Limit parameter ranges
                    if param in validParamRanges:
                        node[param] = util.clip(node[param],
                                *validParamRanges[param])
        print(generateNodeConfig(nodes))

def sweepParamForNode(templateNodes, nodeId, param,
        minPercent, maxPercent, count):
    """ Generate <count> nodeconfigs in which the given param for the given node
    is varied from minPercent to maxPercent of the original value. """

    minRatio = minPercent / 100
    maxRatio = maxPercent / 100

    nodes = deepcopy(templateNodes)
    for i in range(count):
        for j, node in enumerate(nodes):
            if node['nodeId'] == nodeId:
                ratio = (maxRatio - minRatio) / (count - 1) * i + minRatio
                node[param] = templateNodes[j][param] * ratio
                break
        print(generateNodeConfig(nodes))

def generateSet5():
    """
    Similar to generateSet1 - vary one node at a time, one parameter at a time
    """
    generateAllParamSingleVariations(convergeEcosystem3Nodes, 50, 150, 5)

def generateSet6():
    generatePairVariations(convergeEcosystem3Nodes, 'X', 50, 150, 10)

def generateSet7():
    generateTripleVariations(convergeEcosystem3Nodes, 'X', 50, 150, 10)

def generateSet9():
    """
    Generate single-parameter variations on Convergence ecosystem #2
    """
    generateAllParamSingleVariations(
            parseNodeConfig(convergenceNodeConfigs[1]), 50, 150, 5)

def generateSet10():
    """
    Generate single-parameter variations on Convergence ecosystem #4
    """
    generateAllParamSingleVariations(
            parseNodeConfig(convergenceNodeConfigs[3]), 50, 150, 5)

def generateSet11():
    """
    Generate single-parameter variations on Convergence ecosystem #5
    """
    generateAllParamSingleVariations(
            parseNodeConfig(convergenceNodeConfigs[4]), 50, 150, 5)

def generateSet12():
    """
    Generate random variations on Convergence ecosystem #2 (6 species)
    """
    nodes = parseNodeConfig(convergenceNodeConfigs[1])
    generateRandomVariations(nodes, ('initialBiomass', 'K', 'R', 'X'),
            50, 150, 1000)

def generatePerUnitBiomassVariations():
    nodes = parseNodeConfig(convergenceNodeConfigs[1])
    generateRandomVariations(nodes, ('perUnitBiomass',), 50, 150, 100)


def generateGaussianMixtureVariations(templateNodes, distribution, count):
    """
    Generate 'count' node configs based on the given GMM distribution.

    The 'distribution' argument is a data structure returned by
    parse_weka_em_output().

    Attributes are treated independently; Weka's EM clusterer does not estimate
    multivariate Gaussians.
    """

    nodes = deepcopy(templateNodes)

    priors = [component['prior'] for component in distribution]
    cumulativePriors = list(itertools.accumulate(priors))

    # Count the number of times each component was chosen (for testing)
    count_k = [0, 0]

    for i in range(count):

        # Choose a component based on the prior probabilities
        rand = random.random() * cumulativePriors[-1]
        k = bisect.bisect(cumulativePriors, rand)
        count_k[k] += 1
        componentNodes = distribution[k]['nodes']

        # Draw parameter values from the Gaussian distribution defined by
        # componentNodes.
        for node in nodes:
            nodeId = node['nodeId']
            for paramName, distParams in componentNodes[nodeId].items():
                node[paramName] = random.gauss(
                        distParams['mean'], distParams['stdDev'])
        print(generateNodeConfig(nodes))

    # Print number of times each component was chosen (for testing - proportions
    # should match priors)
    #print(count_k)

def makeBaseConfigFromSpeciesList(speciesIdList,
        basalBiomass=1000.0, nonBasalBiomass=1000.0, sort=True):
    speciesData = util.get_species_data()
    nodes = []

    for speciesId in speciesIdList:
        species = speciesData[speciesId]
        if len(species['node_id_list']) > 1:
            raise RuntimeError("Species with multiple nodes not handled yet")
        node = {
            'nodeId': species['node_id_list'][0],
            'perUnitBiomass': species['biomass'],
        }
        if species['organism_type'] == 1:
            # plant
            node['initialBiomass'] = basalBiomass
            node['K'] = species['carrying_capacity']
            node['R'] = species['growth_rate']
        else:
            # animal
            node['initialBiomass'] = nonBasalBiomass
            node['X'] = species['metabolism']

        nodes.append(node)

    if sort:
        # Sort by node ID to avoid triggering bug in unpatched ATNEngine
        nodes.sort(key=lambda n: n['nodeId'])
    # Otherwise, it's assumed speciesIdList is sorted as desired

    return nodes

def generateSet16():
    """
    Generate node configs for an algorithmically-generated 7-species food web.
    Only initial biomass is varied.
    """
    speciesIds = [int(i) for i in '9 19 32 57 61 64 89'.split()]
    templateNodes = makeBaseConfigFromSpeciesList(speciesIds)
    generateRandomVariations(templateNodes, ['initialBiomass'], 20, 200, 1000)

def generateSet17():
    """
    Generate node configs for an algorithmically-generated 7-species food web.
    Only initial biomass is varied.
    """
    speciesIds = [int(i) for i in '9 19 32 57 61 64 89'.split()]
    templateNodes = makeBaseConfigFromSpeciesList(speciesIds)
    generateRandomVariations(templateNodes, ['initialBiomass'], 10, 300, 2000)

def generateSet18():
    """
    Generate node configs for an algorithmically-generated 7-species food web.
    Only initial biomass is varied.
    """
    speciesIds = [int(i) for i in '8 9 31 52 55 1002 1005'.split()]
    templateNodes = makeBaseConfigFromSpeciesList(speciesIds)
    generateRandomVariations(templateNodes, ['initialBiomass'], 10, 300, 2000)

def generateSet19():
    """
    Generate node configs for an algorithmically-generated 5-species food web.
    Only initial biomass is varied.
    """
    speciesIds = [int(i) for i in '9 10 12 25 89'.split()]
    templateNodes = makeBaseConfigFromSpeciesList(speciesIds)
    generateRandomVariations(templateNodes, ['initialBiomass'], 10, 300, 2000)

def generateSet20():
    """
    Generate node configs for an algorithmically-generated 5-species food web.
    Only initial biomass is varied.
    This one gives 10x as much initial biomass to the basal species.
    """
    speciesIds = [int(i) for i in '15 17 26 77 1002'.split()]
    templateNodes = makeBaseConfigFromSpeciesList(speciesIds)
    generateRandomVariations(templateNodes, ['initialBiomass'], 10, 300, 2000)

def generateSet21():
    speciesIds = [int(i) for i in '15 17 26 77 1002'.split()]
    templateNodes = makeBaseConfigFromSpeciesList(speciesIds)
    generateRandomVariations(templateNodes, ['initialBiomass', 'K', 'R', 'X'],
            33, 300, 3000)

def generateSet22():
    speciesIds = [int(i) for i in '42 31 5 85 1005'.split()]
    templateNodes = makeBaseConfigFromSpeciesList(speciesIds)
    generateRandomVariations(templateNodes, ['initialBiomass', 'K', 'R', 'X'],
            50, 200, 1000)
generatorFunctions[22] = generateSet22

def generateSet23():
    speciesIds = [int(i) for i in '72 33 1003 28 51'.split()]
    templateNodes = makeBaseConfigFromSpeciesList(speciesIds)
    generateRandomVariations(templateNodes, ['initialBiomass', 'K', 'R', 'X'],
            50, 200, 1000)
generatorFunctions[23] = generateSet23

def generateSet24():
    speciesIds = [int(i) for i in '1001 87 75 14 33'.split()]
    templateNodes = makeBaseConfigFromSpeciesList(speciesIds)
    generateRandomVariations(templateNodes, ['initialBiomass', 'K', 'R', 'X'],
            50, 200, 1000)
generatorFunctions[24] = generateSet24

def generateSet25():
    speciesIds = [int(i) for i in '16 82 83 1004 86'.split()]
    templateNodes = makeBaseConfigFromSpeciesList(speciesIds)
    generateRandomVariations(templateNodes, ['initialBiomass', 'K', 'R', 'X'],
            50, 200, 1000)
generatorFunctions[25] = generateSet25

def generateSet26():
    speciesIds = [int(i) for i in '65 66 51 85 6 63 74 1003 1004 45 31'.split()]
    templateNodes = makeBaseConfigFromSpeciesList(speciesIds)
    generateRandomVariations(templateNodes, ['initialBiomass', 'K', 'R', 'X'],
            50, 200, 1000)
generatorFunctions[26] = generateSet26

def generateSet27():
    speciesIds = [int(i) for i in '34 22 70 28 40 9 47 1004 1005 14 45'.split()]
    templateNodes = makeBaseConfigFromSpeciesList(speciesIds)
    generateRandomVariations(templateNodes, ['initialBiomass', 'K', 'R', 'X'],
            50, 200, 1000)
generatorFunctions[27] = generateSet27

def generateSet28():
    speciesIds = [int(i) for i in '83 85 6 39 8 44 1002 55 1004 74 31'.split()]
    templateNodes = makeBaseConfigFromSpeciesList(speciesIds)
    generateRandomVariations(templateNodes, ['initialBiomass', 'K', 'R', 'X'],
            50, 200, 1000)
generatorFunctions[28] = generateSet28

def generateSet29():
    speciesIds = [int(i) for i in '64 16 26 69 87 1001 42 1003 45 31'.split()]
    templateNodes = makeBaseConfigFromSpeciesList(speciesIds)
    generateRandomVariations(templateNodes, ['initialBiomass', 'K', 'R', 'X'],
            50, 200, 1000)
generatorFunctions[29] = generateSet29

def generateSet30():
    speciesIds = [int(i) for i in '48 33 82 52 25 17 1001 1003 13 46'.split()]
    templateNodes = makeBaseConfigFromSpeciesList(speciesIds)
    generateRandomVariations(templateNodes, ['initialBiomass', 'K', 'R', 'X'],
            50, 200, 1000)
generatorFunctions[30] = generateSet30

def generateSet31():
    speciesIds = [int(i) for i in '48 66 27 4 85 1001 10 11 1004 45'.split()]
    templateNodes = makeBaseConfigFromSpeciesList(speciesIds)
    generateRandomVariations(templateNodes, ['initialBiomass', 'K', 'R', 'X'],
            50, 200, 1000)
generatorFunctions[31] = generateSet31

def generateSet32():
    speciesIds = [int(i) for i in '2 42 5 72 83 1002 1003 74 14 53'.split()]
    templateNodes = makeBaseConfigFromSpeciesList(speciesIds)
    generateRandomVariations(templateNodes, ['initialBiomass', 'K', 'R', 'X'],
            50, 200, 1000)
generatorFunctions[32] = generateSet32

def generateSet33():
    speciesIds = [int(i) for i in '2 42 5 72 83 1002 1003 74 14 53'.split()]
    templateNodes = makeBaseConfigFromSpeciesList(speciesIds)
    generateRandomVariations(templateNodes, ['initialBiomass', 'K', 'R', 'X'],
            50, 200, 1000)
generatorFunctions[33] = generateSet33

def generateSet34():
    speciesIds = [int(i) for i in '85 70 71 40 41 26 59 1004 1005'.split()]
    templateNodes = makeBaseConfigFromSpeciesList(speciesIds)
    generateRandomVariations(templateNodes, ['initialBiomass', 'K', 'R', 'X'],
            50, 200, 1000)
generatorFunctions[34] = generateSet34

def generateSet35():
    speciesIds = [int(i) for i in '16 21 38 55 1002 1003 28 46 31'.split()]
    templateNodes = makeBaseConfigFromSpeciesList(speciesIds)
    generateRandomVariations(templateNodes, ['initialBiomass', 'K', 'R', 'X'],
            50, 200, 100)
generatorFunctions[35] = generateSet35

def generateSet36():
    speciesIds = [int(i) for i in '16 17 53 1001 1003 77 14 21'.split()]
    templateNodes = makeBaseConfigFromSpeciesList(speciesIds)
    generateRandomVariations(templateNodes, ['initialBiomass', 'K', 'R', 'X'],
            50, 200, 100)
generatorFunctions[36] = generateSet36

def generateSet37():
    speciesIds = [int(i) for i in '16 17 53 1001 1003 77 14 21'.split()]
    templateNodes = makeBaseConfigFromSpeciesList(speciesIds)
    generateRandomVariations(templateNodes, ['initialBiomass', 'K', 'R', 'X'],
            50, 200, 100)
generatorFunctions[37] = generateSet37

def generateSet38():
    speciesIds = [int(i) for i in '80 1 11 69 27 71 1001 1003'.split()]
    templateNodes = makeBaseConfigFromSpeciesList(speciesIds)
    generateRandomVariations(templateNodes, ['initialBiomass', 'K', 'R', 'X'],
            50, 200, 100)
generatorFunctions[38] = generateSet38

def generateSet39():
    speciesIds = [int(i) for i in '80 49 55 8 1002 15'.split()]
    templateNodes = makeBaseConfigFromSpeciesList(speciesIds)
    generateRandomVariations(templateNodes, ['initialBiomass', 'K', 'R', 'X'],
            50, 200, 100)
generatorFunctions[39] = generateSet39

def generateSet40():
    speciesIds = [int(i) for i in '2 42 5 72 83 1002 1003 74 14 53'.split()]
    nodes = makeBaseConfigFromSpeciesList(speciesIds)
    for i in range(10):
        print(generateNodeConfig(nodes))
        random.shuffle(nodes)
generatorFunctions[40] = generateSet40

def generateSet41():
    speciesIds = [int(i) for i in '2 42 5 72 83 1002 1003 74 14 53'.split()]
    nodes = makeBaseConfigFromSpeciesList(speciesIds)
    for i in range(10):
        print(generateNodeConfig(nodes))
        nonBasalNodes = nodes[2:]
        random.shuffle(nonBasalNodes)
        nodes = nodes[0:2] + nonBasalNodes
generatorFunctions[41] = generateSet41

def generateSet42():
    nodes = parseNodeConfig(convergenceNodeConfigs[0])
    for i in range(10):
        print(generateNodeConfig(nodes))
        nonBasalNodes = nodes[1:]
        random.shuffle(nonBasalNodes)
        nodes = nodes[0:1] + nonBasalNodes
generatorFunctions[42] = generateSet42

def generateSet43():
    # Topologically sorted version of set 29
    speciesIds = [int(i) for i in '1003 1001 31 45 87 69 16 26 42 64'.split()]
    templateNodes = makeBaseConfigFromSpeciesList(speciesIds, sort=False)
    generateRandomVariations(templateNodes, ['initialBiomass', 'K', 'R', 'X'],
            50, 200, 1000)
generatorFunctions[43] = generateSet43

def generateSet44():
    speciesIds = [int(i) for i in '72 33 1003 28 51'.split()]
    templateNodes = makeBaseConfigFromSpeciesList(speciesIds)
    sweepParamForNode(templateNodes, 51, 'initialBiomass', 5, 100, 1000)
generatorFunctions[44] = generateSet44

def generateSet45():
    speciesIds = [int(i) for i in '72 33 1003 28 51'.split()]
    templateNodes = makeBaseConfigFromSpeciesList(speciesIds)
    sweepParamForNode(templateNodes, 51, 'X', 5, 100, 1000)
generatorFunctions[45] = generateSet45

def generateSet46():
    speciesIds = [1005, 14, 31, 42, 2]
    templateNodes = makeBaseConfigFromSpeciesList(speciesIds)
    generateRandomVariations(templateNodes, ['initialBiomass', 'K', 'R', 'X'],
            50, 200, 1000)
generatorFunctions[46] = generateSet46

def generateSet47():
    templateNodes = parseNodeConfig(convergenceNodeConfigs[0])
    generateRandomVariations(templateNodes, ['initialBiomass', 'K', 'R', 'X'],
            50, 150, 1000)
generatorFunctions[47] = generateSet47

def generateSet48():
    templateNodes = parseNodeConfig(convergenceNodeConfigs[1])
    generateRandomVariations(templateNodes, ['initialBiomass', 'K', 'R', 'X'],
            50, 150, 1000)
generatorFunctions[48] = generateSet48

def generateSet49():
    speciesIds = [int(i) for i in '80 51 52 71 1001 75'.split()]
    templateNodes = makeBaseConfigFromSpeciesList(speciesIds)
    generateRandomVariations(templateNodes, ['initialBiomass', 'K', 'R', 'X'],
            50, 200, 100)
generatorFunctions[49] = generateSet49

def generateSet50():
    templateNodes = parseNodeConfig(convergenceNodeConfigs[2])
    generateRandomVariations(templateNodes, ['initialBiomass', 'K', 'R', 'X'],
            50, 150, 1000)
generatorFunctions[50] = generateSet50

def generateSet51():
    # Variations on set 47, sim 90
    templateNodes = parseNodeConfig("5,[5],1555.63,1.0,1,K=11091.4,0,[14],1071.01,20.0,1,X=0.254849,0,[31],1844.15,0.0075,1,X=0.517565,0,[42],133.96,0.205,1,X=0.726891,0,[70],2110.84,13.0,1,X=0.194138,0")
    generateRandomVariations(templateNodes, ['K', 'X'], 50, 150, 100)
generatorFunctions[51] = generateSet51

def generateSet52():
    # Variations on set 50, sim 100
    templateNodes = parseNodeConfig("11,[2],645.546,528.0,2,K=1660.64,R=1.0,0,[3],599.66,528.0,1,K=4441.54,0,[4],595.662,528.0,1,K=2754.94,0,[5],1426.75,1.0,1,K=2084.45,0,[7],639.183,816.0,1,K=4015.18,0,[49],1511.23,0.355,1,X=1.0,0,[55],739.104,0.213,1,X=0.496037,0,[61],392.821,54.0,1,X=0.00999599,0,[74],924.06,50.0,1,X=0.115569,0,[82],525.34,50.0,1,X=0.376351,0,[83],233.019,103.0,1,X=0.180538,0")
    generateRandomVariations(templateNodes, ['K', 'X'], 50, 150, 100)
generatorFunctions[52] = generateSet52

def generateSet53():
    """ Like set 42, but shuffle all nodes, not just basal """
    nodes = parseNodeConfig(convergenceNodeConfigs[0])
    for i in range(10):
        print(generateNodeConfig(nodes))
        random.shuffle(nodes)
generatorFunctions[53] = generateSet53

def generateSet54():
    templateNodes = makeBaseConfigFromSpeciesList([73, 1003, 61, 55, 33])
    generateRandomVariations(templateNodes, ['initialBiomass'], 25, 175, 1000)
generatorFunctions[54] = generateSet54

def generateSet55():
    templateNodes = makeBaseConfigFromSpeciesList([73, 1003, 61, 55, 33])
    sweepParamForNode(templateNodes, 3, 'R', 10, 300, 100)
generatorFunctions[55] = generateSet55

def generateSet56():
    templateNodes = makeBaseConfigFromSpeciesList([73, 1003, 61, 55, 33])
    sweepParamForNode(templateNodes, 3, 'initialBiomass', 50, 500, 100)
generatorFunctions[56] = generateSet56

def generateSet57():
    templateNodes = makeBaseConfigFromSpeciesList([8, 4, 1002, 36, 14])
    generateRandomVariations(templateNodes, ['initialBiomass'], 25, 175, 1000)
generatorFunctions[57] = generateSet57

def generateSet58():
    templateNodes = makeBaseConfigFromSpeciesList([65, 50, 1003, 55, 33])
    generateRandomVariations(templateNodes, ['initialBiomass'], 25, 175, 1000)
generatorFunctions[58] = generateSet58

def generateSet59():
    templateNodes = makeBaseConfigFromSpeciesList([1002, 36, 14, 46, 31])
    generateRandomVariations(templateNodes, ['initialBiomass'], 25, 175, 1000)
generatorFunctions[59] = generateSet59

def generateSet60():
    templateNodes = makeBaseConfigFromSpeciesList(
            [66, 83, 82, 53, 71, 88, 1001, 7, 1004, 1005])
    generateRandomVariations(templateNodes, ['initialBiomass'], 25, 175, 1000)
generatorFunctions[60] = generateSet60

def generateSet61():
    templateNodes = makeBaseConfigFromSpeciesList(
            [88, 2, 4, 21, 87, 8, 1001, 1002, 1003, 14]
            )
    generateRandomVariations(templateNodes, ['initialBiomass'], 25, 175, 1000)
generatorFunctions[61] = generateSet61

def generateSet62():
    templateNodes = makeBaseConfigFromSpeciesList(
            [49, 83, 53, 28, 1001, 42, 1003, 1004, 85, 44]
            )
    generateRandomVariations(templateNodes, ['initialBiomass'], 25, 175, 1000)
generatorFunctions[62] = generateSet62

def generateSet63():
    templateNodes = makeBaseConfigFromSpeciesList(
            [80, 66, 1003, 4, 31]
            )
    generateRandomVariations(templateNodes, ['initialBiomass'], 25, 175, 1000)
generatorFunctions[63] = generateSet63

def generateSet64():
    templateNodes = makeBaseConfigFromSpeciesList(
            [80, 49, 82, 50, 69, 71, 88, 1001, 1003, 1005]
            )
    generateRandomVariations(templateNodes, ['initialBiomass'], 25, 175, 1000)
generatorFunctions[64] = generateSet64

def generateSet65():
    origNodes = makeBaseConfigFromSpeciesList(
            [53, 73, 74, 80, 1005]
            )
    print(generateNodeConfig(origNodes))
generatorFunctions[65] = generateSet65
 
def generateSet66():
    origNodes = makeBaseConfigFromSpeciesList(
            [47, 49, 83, 86, 1003]
            )
    print(generateNodeConfig(origNodes))
generatorFunctions[66] = generateSet66

def generateSet67():
    templateNodes = makeBaseConfigFromSpeciesList(
            [39, 80, 31, 72, 1003]
            )
    generateRandomVariations(templateNodes, ['initialBiomass', 'K', 'R', 'X'],
            50, 150, 1000)
generatorFunctions[67] = generateSet67

def generateSet68():
    templateNodes = makeBaseConfigFromSpeciesList(
            [49, 4, 18, 50, 36, 9, 85, 14, 8, 1002]
            )
    generateRandomVariations(templateNodes, ['initialBiomass', 'K', 'R', 'X'],
            50, 150, 1000)
generatorFunctions[68] = generateSet68

def generateSet69():
    templateNodes = makeBaseConfigFromSpeciesList(
            [3, 49, 41, 86, 47, 61, 83, 33, 1004, 1005]
            )
    generateRandomVariations(templateNodes, ['initialBiomass', 'K', 'R', 'X'],
            50, 150, 1000)
generatorFunctions[69] = generateSet69

def printUsageAndExit():
    print("Usage: ./nodeconfig_generator.py <set#>", file=sys.stderr)
    sys.exit(1)

if __name__ == '__main__':

    # Starting with set 22, putting generator functions in a dict, so the set
    # can be chosen from the command line

    if len(sys.argv) != 2:
        printUsageAndExit()
    try:
        setNumber = int(sys.argv[1])
    except ValueError:
        printUsageAndExit()

    if setNumber not in generatorFunctions:
        print("Invalid set number (valid set numbers: {})".format(
            ' '.join(map(str, generatorFunctions.keys()))),
            file=sys.stderr)
        printUsageAndExit()

    generatorFunctions[setNumber]()
