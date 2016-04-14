#!/usr/bin/env python3

# Ben Saylor
# October 2015

from copy import copy, deepcopy
import random
import re
import itertools
import bisect

import util

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
                paramConfig += '{}={:.6},'.format(param, node[param])
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
    for i in range(count):
        for j, node in enumerate(nodes):
            for param in node.keys():
                if param in params:
                    node[param] = (templateNodes[j][param] *
                            random.uniform(minRatio, maxRatio))
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

def parseWekaEMOutput(priors, text):
    """
    Parse the portion of the output from Weka's EM clusterer that gives the
    distribution parameters for each attribute.  Doesn't parse cluster priors;
    they must be supplied as an argument.  The return value is a list of
    dictionaries - one for each cluster - structured like the following example:
    
[
    {
        "prior": 0.35,
        "nodes": {
            "5": {
                "K": {
                    "mean": 8025.473,
                    "stdDev": 2253.5472
                },
                "initialBiomass": {
                    "mean": 2085.6366,
                    "stdDev": 506.5151
                }
            },
            "14": {
                "X": {
                    "mean": 0.2048,
                    "stdDev": 0.0588
                },
                "initialBiomass": {
                    "mean": 669.0392,
                    "stdDev": 91.3827
                }
            }
        }
    },
    
    {
        "prior": 0.65,
        "nodes": {
            "5": {
                "K": {
                    "mean": 8326.2055,
                    "stdDev": 2189.6134
                },
                "initialBiomass": {
                    "mean": 2023.5001,
                    "stdDev": 578.9036
                }
            },
            "14": {
                "X": {
                    "mean": 0.2043,
                    "stdDev": 0.0585
                },
                "initialBiomass": {
                    "mean": 1185.7895,
                    "stdDev": 231.4305
                }
            }
        }
    }
]
    """
    
    dist = [{'prior': p, 'nodes': {}} for p in priors]
    
    for line in text.split('\n'):
        if len(line.strip()) == 0:
            # skip blank line
            continue
        firstDigitPos = re.search(r'\d', line).start()
        if line[0] != ' ':
            # Found a line giving the attribute name
            paramName = line[:firstDigitPos]
            nodeId = int(line[firstDigitPos:])
        else:
            # Found a line giving means or standard deviations for an attribute
            if line.lstrip().startswith('mean'):
                distParamName = 'mean'
            if line.lstrip().startswith('std. dev.'):
                distParamName = 'stdDev'
            for k, distParamValue in enumerate(
                    [float(x) for x in line[firstDigitPos:].split()]):
                if nodeId not in dist[k]['nodes']:
                    dist[k]['nodes'][nodeId] = {}
                if paramName not in dist[k]['nodes'][nodeId]:
                    dist[k]['nodes'][nodeId][paramName] = {}
                dist[k]['nodes'][nodeId][paramName][distParamName] = distParamValue
    
    return dist

def generateGaussianMixtureVariations(templateNodes, distribution, count):
    """
    Generate 'count' node configs based on the given GMM distribution.

    The 'distribution' argument is a data structure returned by
    parseWekaEMOutput().

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

def makeBaseConfigFromSpeciesList(speciesIdList):
    speciesData = util.get_species_data()
    nodes = []

    # Sort species by trophic level (ATNEngine needs plants first)
    speciesIdList.sort(key=lambda i: speciesData[i]['trophic_level'])

    for speciesId in speciesIdList:
        species = speciesData[speciesId]
        if len(species['node_id_list']) > 1:
            raise RuntimeError("Species with multiple nodes not handled yet")
        node = {
            'nodeId': species['node_id_list'][0],
            'initialBiomass': 1000.0,
            'perUnitBiomass': species['biomass'],
        }
        if species['organism_type'] == 1:
            # plant
            node['K'] = species['carrying_capacity']
            node['R'] = species['growth_rate']
        else:
            # animal
            node['X'] = species['metabolism']

        nodes.append(node)

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

if __name__ == '__main__':
    pass
    #generateSet1()
    #generateSet2()
    #generateSet3()
    #generateSet4()
    #generateSet5()
    #generateSet6()
    #generateSet7()
    #generateSet9()
    #generateSet10()
    #generateSet11()
    #generateSet12()
    #generatePerUnitBiomassVariations()

    wekaEMOutput = """
K5
  mean               8025.473 8326.2055
  std. dev.         2253.5472 2189.6134

X14
  mean                 0.2048    0.2043
  std. dev.            0.0588    0.0585

X31
  mean                 0.6112    0.5995
  std. dev.            0.0789    0.0771

X33
  mean                 0.3854    0.3738
  std. dev.             0.109    0.1113

X56
  mean                 0.1951    0.1759
  std. dev.            0.0522    0.0528

X59
  mean                 0.2167    0.2203
  std. dev.            0.0693    0.0649

initialBiomass14
  mean               669.0392 1185.7895
  std. dev.           91.3827  231.4305

initialBiomass31
  mean                30.3852   28.9353
  std. dev.            7.8386    8.6399

initialBiomass33
  mean              2455.4004 2556.0225
  std. dev.          681.7782  709.3693

initialBiomass5
  mean              2085.6366 2023.5001
  std. dev.          506.5151  578.9036

initialBiomass56
  mean               702.9477  722.2053
  std. dev.          205.0646  205.3958

initialBiomass59
  mean               661.6127  704.5754
  std. dev.          206.5186  188.6952

perUnitBiomass14
  mean                     20        20
  std. dev.                 0         0

perUnitBiomass31
  mean                  0.008     0.008
  std. dev.                 0         0

perUnitBiomass33
  mean                    0.4       0.4
  std. dev.                 0         0

perUnitBiomass5
  mean                      1         1
  std. dev.                 0         0

perUnitBiomass56
  mean                   6.25      6.25
  std. dev.                 0         0

perUnitBiomass59
  mean                   3.35      3.35
  std. dev.                 0         0
    """

    #templateNodes = parseNodeConfig(convergenceNodeConfigs[1])
    #dist = parseWekaEMOutput([0.35, 0.65], wekaEMOutput)
    #generateGaussianMixtureVariations(templateNodes, dist, 1000)

    generateSet16()
    #generateSet17()
    #generateSet18()
