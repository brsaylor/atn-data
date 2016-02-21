#!/usr/bin/env python3

"""
Ben Saylor
November 2015, January 2016

Process a set of biomass data files (ATN*.csv) - one file per simulation -
create a summary CSV file with one row per simulation with various features
calculated from the biomass data.
"""

import sys
import os.path
import csv
from math import log2

import numpy as np
from scipy import stats, signal

from nodeconfig_generator import parseNodeConfig

NO_EXTINCTION = 99999999

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
    Given a node config as returned by parseNodeConfig(), return a dictionary
    with one key-value pair for each node-parameter pair, where the keys are
    named with the parameter name with the node ID appended.
    """
    params = {}
    for node in nodeConfig:
        for key, value in node.items():
            if key == 'nodeId':
                continue
            params[key + str(node['nodeId'])] = value
    return params

def getSpeciesData(filename='species-data.csv'):
    """
    Given the filename of the CSV containing species-level data (for all
    species, rows unique by nodeId),
    return a dict whose keys are node IDs and keys are dicts containing the data
    for that species.
    """

    data = {}
    with open(filename, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            data[int(row['nodeId'])] = {
                'name': row['name'],
                'trophicLevel': float(row['trophicLevel'])
            }
    return data

def getSimulationData(filename):
    """
    Given a filename of an ATN CSV file,
    return a tuple (nodeConfig, nodeConfigAttributes, biomassData).

    nodeConfigAttributes is a dictionary with the node config parameters (as
    returned by nodeConfigToParams()).

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
        nodeConfigStr = row[0].split(': ')[1]
        nodeConfig = parseNodeConfig(nodeConfigStr)
        nodeConfigAttributes = nodeConfigToParams(nodeConfig)

    return (nodeConfig, nodeConfigAttributes, biomassData)

def environmentScore(speciesData, nodeConfig, biomassData):
    """
    Compute the Environment Score for all timesteps for the given data and
    return the score time series.  The calculations are taken from
    model.Ecosystem.updateEcosystemScore() in WoB_Server.
    """

    numTimesteps = len(biomassData[nodeConfig[0]['nodeId']])
    scores = np.empty(numTimesteps)

    for timestep in range(numTimesteps):

        # Calculate the Ecosystem Score for this timestep
        biomass = 0
        numSpecies = 0
        for node in nodeConfig:
            nodeId = node['nodeId']
            perUnitBiomass = node['perUnitBiomass']

            # Sometimes biomass can go slightly negative.
            # Clip to 0 to avoid complex numbers in score calculation.
            totalBiomass = max(0, biomassData[nodeId][timestep])

            if totalBiomass > 0:
                numSpecies += 1

            biomass += perUnitBiomass * pow(totalBiomass / perUnitBiomass,
                    speciesData[nodeId]['trophicLevel'])
        if biomass > 0:
            biomass = round(log2(biomass)) * 5
        scores[timestep] = int(round(pow(biomass, 2) + pow(numSpecies, 2)))

    return scores

def getAvgEcosystemScore(speciesData, nodeConfig, biomassData):
    return environmentScore(speciesData, nodeConfig, biomassData).mean()

def totalBiomass(speciesData, nodeConfig, biomassData):
    """
    Return a time series of the total biomass of all species
    """
    numTimesteps = len(biomassData[nodeConfig[0]['nodeId']])
    totalBiomass = np.empty(numTimesteps)
    for timestep in range(numTimesteps):
        totalBiomass[timestep] = sum(
                [biomass[timestep] for biomass in biomassData.values()])
    return totalBiomass

def netProduction(speciesData, nodeConfig, biomassData):
    """
    Time-series measure of ecosystem health
    computed as net production (change/derivative in total biomass)
    """
    B = totalBiomass(speciesData, nodeConfig, biomassData)
    netProd = B - np.roll(B, 1)
    
    # Can't really say that net production was equal to total biomass at t0
    netProd[0] = netProd[-1] = 0
    
    return netProd

def shannonIndexBiomassProduct(speciesData, nodeConfig, biomassData):
    """
    Time-series measure of ecosystem health
    computed as the product of the Shannon index (based on biomass)
    and the total biomass.
    """
    numTimesteps = len(biomassData[nodeConfig[0]['nodeId']])
    scores = np.zeros(numTimesteps)
    
    for timestep in range(numTimesteps):
        speciesBiomass = np.empty(len(nodeConfig))
        for i, node in enumerate(nodeConfig):
            speciesBiomass[i] = max(0, biomassData[node['nodeId']][timestep])
        totalBiomass = speciesBiomass.sum()
        for i, node in enumerate(nodeConfig):
            if speciesBiomass[i] <= 0:
                continue
            proportion = speciesBiomass[i] / totalBiomass
            scores[timestep] -= proportion * log2(proportion)
        scores[timestep] *= totalBiomass
    
    return scores

def shannonIndexBiomassProductNorm(speciesData, nodeConfig, biomassData):
    """
    A version of shannonIndexBiomassProduct normalized by initial total biomass
    and maximum possible Shannon index for the number of species,
    enabling more meaningful comparison across ecosystems of different sizes.
    """

    totalInitialBiomass = sum(
            [biomass[0] for biomass in biomassData.values()])
    perfectShannon = 0
    for i, node in enumerate(nodeConfig):
        proportion = 1 / len(nodeConfig)
        perfectShannon -= proportion * log2(proportion)
    return (shannonIndexBiomassProduct(speciesData, nodeConfig, biomassData)
            / (totalInitialBiomass * perfectShannon))

def getOutputAttributes(speciesData, nodeConfig, biomassData):
    """
    Given speciesData as returned by getSpeciesData,
    nodeConfig and biomassData as returned by getSimulationData,
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
    avgEcosystemScore: average EcosystemScore over all timesteps
    """

    # Output attributes
    out = {}

    numSpecies = len(biomassData)
    surviving20 = numSpecies
    surviving1000 = numSpecies
    extinctionTimesteps = []

    for nodeId, biomassSeries in biomassData.items():
        numTimesteps = len(biomassSeries)
        cumulativeBiomass = 0
        cumulativeBiomass2 = 0
        extinct = False
        out['extinction_' + str(nodeId)] = NO_EXTINCTION
        for timestep, biomass in enumerate(biomassSeries):
            if not extinct:
                if biomass == 0:
                    out['extinction_' + str(nodeId)] = timestep
                    extinctionTimesteps.append(timestep)
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

    #
    # Scalar measures of ecosystem health
    #

    # Average of original environment score formula
    out['avgEcosystemScore'] = getAvgEcosystemScore(
            speciesData, nodeConfig, biomassData)

    t = np.arange(numTimesteps)

    # Slope of linear regression of shannonIndexBiomassProduct
    health = shannonIndexBiomassProduct(
            speciesData, nodeConfig, biomassData)
    slope, intercept, r_value, p_value, std_err = stats.linregress(
            t, health)
    out['shannonBiomassSlope'] = slope

    # Slope of linear regression of shannonIndexBiomassProduct
    health = shannonIndexBiomassProductNorm(
            speciesData, nodeConfig, biomassData)
    slope, intercept, r_value, p_value, std_err = stats.linregress(
            t, health)
    out['shannonBiomassNormSlope'] = slope

    # Slope of linear regression on local peaks in net production
    netProd = netProduction(
            speciesData, nodeConfig, biomassData)
    # Without smoothing, there are many tiny local peaks
    smoothedNetProd = np.convolve(netProd, np.hanning(20), mode='same')
    maxIndices, = signal.argrelmax(smoothedNetProd)
    maxValues = np.take(netProd, maxIndices)
    out['peakNetProductionSlope'] = stats.linregress(maxIndices, maxValues)[0]

    # Slope of linear regression on environment score
    scores = environmentScore(speciesData, nodeConfig, biomassData)
    out['environmentScoreSlope'] = stats.linregress(t, scores)[0]
    # Slope of log-linear regression on environment score
    out['environmentScoreLogSlope'] = stats.linregress(t, np.log(scores))[0]

    return out

if __name__ == '__main__':
    if len(sys.argv) < 4:
        print("Usage: create_feature_file.py <set#> <outfile.csv> ATN.csv [ATN_1.csv ...]")
        sys.exit(1)

    setNumber = int(sys.argv[1])
    outfilename = sys.argv[2]
    infilenames = sys.argv[3:]

    speciesData = getSpeciesData()

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
        nodeConfig, inputAttributes, biomassData = getSimulationData(infilename)
        outrow.update(inputAttributes)
        outputAttributes = getOutputAttributes(
                speciesData, nodeConfig, biomassData)
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
