#!/usr/bin/env python3

"""
Ben Saylor
November 2015

Process a set of biomass data files (ATN*.csv) - one file per simulation -
create a summary CSV file with one row per simulation with various features
calculated from the biomass data.
"""

import sys
import os.path
import csv

from nodeconfig_generator import parseNodeConfig

def getSimNumber(filename):
    """
    Based on a filename such as
    ATN.csv
    ATN_1.csv
    ATN_123.csv
    return the simulation number such as
    0
    1
    123
    """
    split1 = os.path.basename(filename).split('_')
    if len(split1) == 1:
        return 0
    else:
        return int(split1[1].split('.')[0])

def nodeConfigToParams(nodeConfig):
    """
    Given a node config string, return a dictionary with one key-value pair for
    each node-parameter pair, where the keys are named with the parameter name
    with the node ID appended.
    """
    nodes = parseNodeConfig(nodeConfig)
    params = {}
    for node in nodes:
        for key, value in node.items():
            if key == 'nodeId':
                continue
            params[key + str(node['nodeId'])] = value
    return params

def getSimulationData(filename):
    """
    Given a filename of an ATN CSV file,
    return a tuple (nodeConfigAttributes, biomassData).

    nodeConfigAttributes is a dictionary with the node config parameters (as
    returned by nodeConfigParams()).

    biomassData is a dictionary mapping node ID to a list of biomass values over
    time.
    """

    nodeConfigAttributes = None
    biomassData = {}

    with open(filename, 'r') as f:
        reader = csv.reader(f)
        reader.__next__()  # Skip the header row
        for row in reader:
            if len(row) == 0 or row[0] == '':
                # Blank line: end of biomass data
                break
            nodeId = int(row[0].split('.')[1])
            biomassData[nodeId] = [int(x) for x in row[1:]]

        # The next row should have the node config
        row = reader.__next__()
        nodeConfig = row[0].split(': ')[1]
        nodeConfigAttributes = nodeConfigToParams(nodeConfig)

    return (nodeConfigAttributes, biomassData)

def getOutputAttributes(biomassData):
    """
    Given biomassData as returned by getSimulationData,
    return a dictionary of attributes whose keys are
    "<attributeName>_<nodeId>" for species-specific attributes and
    "<attributeName>"          for non-species-specific attributes

    Species-specific attributes
    ---------------------------
    avgBiomass: average pre-extinction biomass over all timesteps
    avgBiomass2: average biomass, regardless of extinction, over all timesteps
    extinction: timestep at which the species' biomass first reached 0

    Non-species-specific attributes
    -------------------------------
    surviving20: number of species surviving at timestep 20
    surviving1000: number of species surviving at timestep 1000
    """

    # Output attributes
    out = {}

    numSpecies = len(biomassData)
    surviving20 = numSpecies
    surviving1000 = numSpecies

    for nodeId, biomassSeries in biomassData.items():
        numTimesteps = len(biomassSeries)
        cumulativeBiomass = 0
        cumulativeBiomass2 = 0
        extinct = False
        out['extinction_' + str(nodeId)] = 99999999
        for timestep, biomass in enumerate(biomassSeries):
            if not extinct:
                if biomass == 0:
                    out['extinction_' + str(nodeId)] = timestep
                    extinct = True
                    if timestep <= 20:
                        surviving20 -= 1
                    if timestep <= 1000:
                        surviving1000 -= 1
                else:
                    cumulativeBiomass += biomass
            cumulativeBiomass2 += biomass
        out['avgBiomass_' + str(nodeId)] = (cumulativeBiomass
                / float(numTimesteps))
        out['avgBiomass2_' + str(nodeId)] = (cumulativeBiomass2
                / float(numTimesteps))

    out['surviving20'] = surviving20
    out['surviving1000'] = surviving1000

    return out

if __name__ == '__main__':
    if len(sys.argv) < 4:
        print("Usage: create_feature_file.py <set#> <outfile.csv> ATN.csv [ATN_1.csv ...]")
        sys.exit(1)

    setNumber = int(sys.argv[1])
    outfilename = sys.argv[2]
    infilenames = sys.argv[3:]

    outfile = None
    writer = None

    for simNumber, infilename in sorted(
            [(getSimNumber(f), f) for f in infilenames]):

        # Create the output row from the simulation identifiers, input and
        # output attributes
        outrow = {}
        identifiers = {
                'filename': os.path.basename(infilename),
                'setNumber': setNumber,
                'simNumber': simNumber,
                }
        outrow.update(identifiers)
        inputAttributes, biomassData = getSimulationData(infilename)
        outrow.update(inputAttributes)
        outputAttributes = getOutputAttributes(biomassData)
        outrow.update(outputAttributes)

        if writer is None:
            # Set up the CSV writer

            fieldnames = (
                    list(identifiers.keys()) +
                    sorted(inputAttributes.keys()) +
                    sorted(outputAttributes.keys()))
            outfile = open(outfilename, 'w')
            writer = csv.DictWriter(outfile, fieldnames)
            writer.writeheader()

        writer.writerow(outrow)

    if outfile is not None:
        outfile.close()
