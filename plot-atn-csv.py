#!/usr/bin/env python3

# Ben Saylor
# October 2015

"""
Plot a CSV output by ATNEngine
"""

import sys
import csv
import re

import matplotlib.pyplot as plt

def plotCsv(filename):

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
    nodeConfig = row[0].split(': ')[1]

    # node config split into one string per node
    nodeConfigSplit = ['[' + s for s in nodeConfig.split('[')[1:]]

    f.close()

    for nodeConfigSection in nodeConfigSplit:
        match = re.match(r'\[(\d+)\]', nodeConfigSection)
        nodeId = int(match.group(1))
        plt.plot(data[nodeId])
    plt.xlabel("timestep")
    plt.ylabel("biomass")
    plt.legend(nodeConfigSplit)
    plt.title(filename)
    plt.show()

if __name__ == '__main__':
    filenames = sys.argv[1:]
    for filename in filenames:
        plotCsv(filename)
