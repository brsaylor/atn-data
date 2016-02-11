#!/usr/bin/env python3

# Ben Saylor
# October 2015

from copy import copy, deepcopy

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
    generateSet11()
