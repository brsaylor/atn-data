#!/usr/bin/env python3

# Ben Saylor
# October 2015

"""
Plot a CSV output by ATNEngine
"""

import sys
import csv
import re
import json

import matplotlib.pyplot as plt
import numpy as np
from scipy import stats, signal

from create_feature_file import getSpeciesData, ecosystemScoreSeries
from nodeconfig_generator import parseNodeConfig

speciesData = None

def plotCsv(filename):
    global speciesData
    if speciesData is None:
        speciesData = getSpeciesData()
    
    f = open(filename)
    reader = csv.reader(f)

    reader.__next__() # skip header row

    # data rows indexed by nodeId
    data = {}

    for row in reader:
        if len(row) == 0 or row[0] == '':
            # Blank line: end of biomass data
            break
        nodeId = int(row[0].split('.')[1])
        data[nodeId] = [float(x) for x in row[1:]]

    # The next row should have the node config
    row = reader.__next__()
    nodeConfigStr = row[0].split(': ')[1]
    nodeConfig = parseNodeConfig(nodeConfigStr)

    # node config split into one string per node
    nodeConfigSplit = ['[' + s for s in nodeConfigStr.split('[')[1:]]

    f.close()

    fig, ax1 = plt.subplots(figsize=(14, 8))
    ax1.set_xlabel("timestep")
    ax1.set_ylabel("biomass")
    legend = []
    for nodeConfigSection in nodeConfigSplit:
        match = re.match(r'\[(\d+)\]', nodeConfigSection)
        nodeId = int(match.group(1))
        plt.plot(data[nodeId])
        legend.append(speciesData[nodeId]['name'] + ' ' + nodeConfigSection)
    ax1.legend(legend)

    scores = ecosystemScoreSeries(speciesData, nodeConfig, data)
    ax2 = ax1.twinx()
    ax2.plot(scores, linewidth=2)
    #ax2.legend(['score'])  # gets drawn on top of main legend
    ax2.set_ylabel("score")

    # Linear regression
    t = np.arange(len(scores))
    tn = len(scores) - 1
    slope, intercept, r_value, p_value, std_err = stats.linregress(
            t, scores)
    ax2.plot([0, tn], [intercept, slope * tn + intercept])

    # Regions between local "maxima" (may be plateaus due to rounding)
    # To round off plateaus, do some smoothing by convolving with a Hanning
    # window
    smoothed = np.convolve(scores, np.hanning(20), mode='same')
    maxIndices, = signal.argrelmax(smoothed)
    maxValues = np.take(scores, maxIndices)
    ax2.plot(maxIndices, maxValues, 'r^')
    #
    regions = np.split(scores, maxIndices)
    regionAverages = [region.mean() for region in regions]
    regionCenters = np.empty(len(regions))
    tprev = 0
    for i, t in enumerate(maxIndices):
        regionCenters[i] = (tprev + t) / 2
        tprev = t
    regionCenters[-1] = (tprev + len(scores)) / 2
    ax2.plot(regionCenters, regionAverages, 'ro')

    plt.title(filename)
    plt.show()

    print("TREND MEASURES:")
    print("sum of derivative: {}".format(sumDerivative(scores)))
    print("linear regression: slope = {}, intercept = {}".format(
        slope, intercept))
    print("regionAverages[-2] - regionAverages[1] = {}".format(
        regionAverages[-2] - regionAverages[1]))

    print("\nSPECIES DATA:")
    printSpeciesData(speciesData, nodeConfig)

def printSpeciesData(speciesData, nodeConfig):
    """
    Print out a formatted JSON representation of the node config and
    species-level data
    """
    dataByNodeId = {}
    for node in nodeConfig:
        nodeId = node['nodeId']
        data = {}
        data.update(node)
        data.update(speciesData[nodeId])
        dataByNodeId[nodeId] = data
    print(json.dumps(dataByNodeId, indent=4, sort_keys=True))

# FIXME: Refactoring needed
def sumDerivative(series):
    # Note: sum of finite-difference derivative is last value minus first
    # value
    return series[-1] - series[0]

if __name__ == '__main__':
    filenames = sys.argv[1:]
    for filename in filenames:
        plotCsv(filename)
