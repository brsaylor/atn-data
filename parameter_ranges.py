#!/usr/bin/env python3

"""
Determine "good" ranges for parameters based on EM clustering of top 25% of
simulations
"""

import sys

from nodeconfig_generator import parseWekaEMOutput, parseNodeConfig

def getRangeForParameter(clusters, nodeId, param):
    """
    Derive a range of "good" values for a parameter based on an EM-GMM
    clustering of 'good' simulations. The bottom of the range is the minimum
    (mean - stdev) for the parameter, and the top of each range is the maximum
    (mean + stdev).
    clusters: output of parseWekaEMOutput
    """
    paramRange = [-1, -1]
    for cluster in clusters:
        mean = cluster['nodes'][nodeId][param]['mean']
        stdDev = cluster['nodes'][nodeId][param]['stdDev']
        rmin = mean - stdDev
        rmax = mean + stdDev
        if paramRange[0] == -1 or rmin < paramRange[0]:
            paramRange[0] = rmin
        if paramRange[1] == -1 or rmax > paramRange[1]:
            paramRange[1] = rmax

    # The preferred location text file values fall within the ranges for each type of parameter:
    # X:  0 -> 1
    # K: 1000 -> 15000
    # R: 0 -> 3
    if paramRange[0] < 0 or param == 'K' and paramRange[0] <= 1000:
        paramRange[0] = -1
    if (
            (param == 'X' and paramRange[1] >= 1) or
            (param == 'K' and paramRange[1] >= 15000) or
            (param == 'R' and paramRange[1] >= 3)):
        paramRange[1] = -1

    return paramRange

def printParamRanges(nodeConfig, trimmedWekaOutputFilename, numClusters):
    nodes = parseNodeConfig(nodeConfig)
    wekaOutput = ''
    with open(trimmedWekaOutputFilename) as f:
        wekaOutput = f.read()
    
    # we don't actually use the priors, but parseWekaOutput() needs them and
    # doesn't determine the number of clusters itself
    priors = [0] * numClusters

    clusters = parseWekaEMOutput(priors, wekaOutput)

    rangeValues = []
    for node in nodes:
        if 'K' in node:
            paramRange = getRangeForParameter(clusters, node['nodeId'], 'K')
            rangeValues.extend(paramRange)
        else:
            paramRange = getRangeForParameter(clusters, node['nodeId'], 'X')
            rangeValues.extend(paramRange)
    print(','.join(map(str, rangeValues)))

if __name__ == '__main__':
    if len(sys.argv) < 4:
        print("Usage: ./parameter_ranges.py <nodeconfig> <trimmed-weka-EM-output-file> <num-clusters>")
        sys.exit(1)

    printParamRanges(sys.argv[1], sys.argv[2], int(sys.argv[3]))
