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

    plt.title(filename)
    plt.show()

    printSpeciesData(speciesData, nodeConfig)

def printSpeciesData(speciesData, nodeConfig):
    dataByNodeId = {}
    for node in nodeConfig:
        nodeId = node['nodeId']
        data = {}
        data.update(node)
        data.update(speciesData[nodeId])
        dataByNodeId[nodeId] = data
    print(json.dumps(dataByNodeId, indent=4, sort_keys=True))

if __name__ == '__main__':
    filenames = sys.argv[1:]
    for filename in filenames:
        plotCsv(filename)
