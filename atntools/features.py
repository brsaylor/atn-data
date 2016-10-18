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
import gzip
import csv
from math import log2

import numpy as np
from scipy import stats, signal
import pandas as pd

from atntools.nodeconfig_generator import parse_node_config

NO_EXTINCTION = 99999999

def get_sim_number(filename):
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

def node_config_to_params(node_config):
    """
    Given a node config as returned by parseNodeConfig(), return a dictionary
    with one key-value pair for each node-parameter pair, where the keys are
    named with the parameter name with the node ID appended.
    """
    params = {}
    for node in node_config:
        for key, value in node.items():
            if key == 'nodeId':
                continue
            params[key + str(node['nodeId'])] = value
    return params

def get_species_data(filename=None):
    """
    Given the filename of the CSV containing species-level data (for all
    species, rows unique by nodeId),
    return a dict whose keys are node IDs and keys are dicts containing the data
    for that species.
    """

    if filename is None:
        filename = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                'data/species-data.csv')

    data = {}
    with open(filename, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            data[int(row['nodeId'])] = {
                'name': row['name'],
                'trophicLevel': float(row['trophicLevel'])
            }
    return data

def get_simulation_data(filename):
    """
    Given a filename of an ATN CSV file,
    return a tuple (node_config, node_config_attributes, biomass_data).

    node_config_attributes is a dictionary with the node config parameters (as
    returned by nodeConfigToParams()).

    biomass_data is a dictionary mapping node ID to a list of biomass values over
    time.
    """

    node_config_attributes = None
    biomass_data = {}

    with (gzip.open(filename, 'rt') if filename.endswith('gz')
            else open(filename, 'r')) as f:
        reader = csv.reader(f)
        reader.__next__()  # Skip the header row
        for row in reader:
            if len(row) == 0 or row[0] == '':
                # Blank line: end of biomass data
                break
            nodeId = int(row[0].split('.')[1])
            biomass_data[nodeId] = [int(x) for x in row[1:]]

        # The next row should have the node config
        row = reader.__next__()
        node_config_str = row[0].split(': ')[1]
        node_config = parse_node_config(node_config_str)
        node_config_attributes = node_config_to_params(node_config)

    return (node_config, node_config_attributes, biomass_data)

def rmse(df1, df2):
    """ Calculate the root mean squared error between the two DataFrames and
    return as a Series indexed by node ID. The sum of this series is the score
    for an attempt in the Convergence game. """
    return np.sqrt(((df1 - df2) ** 2).mean())

def environment_score(species_data, node_config, biomass_data):
    """
    Compute the Environment Score for all timesteps for the given data and
    return the score time series.  The calculations are taken from
    model.Ecosystem.updateEcosystemScore() in WoB_Server.
    """

    num_timesteps = len(biomass_data[node_config[0]['nodeId']])
    scores = np.empty(num_timesteps)

    for timestep in range(num_timesteps):

        # Calculate the Ecosystem Score for this timestep
        biomass = 0
        num_species = 0
        for node in node_config:
            node_id = node['nodeId']
            per_unit_biomass = node['perUnitBiomass']

            # Sometimes biomass can go slightly negative.
            # Clip to 0 to avoid complex numbers in score calculation.
            total_biomass = max(0, biomass_data[node_id][timestep])

            if total_biomass > 0:
                num_species += 1

            biomass += per_unit_biomass * pow(total_biomass / per_unit_biomass,
                                              species_data[node_id]['trophicLevel'])
        if biomass > 0:
            biomass = round(log2(biomass)) * 5
        scores[timestep] = int(round(pow(biomass, 2) + pow(num_species, 2)))

    return scores

def get_avg_ecosystem_score(species_data, node_config, biomass_data):
    return environment_score(species_data, node_config, biomass_data).mean()

def total_biomass(speciesData, node_config, biomass_data):
    """
    Return a time series of the total biomass of all species
    """
    num_timesteps = len(biomass_data[node_config[0]['nodeId']])
    total_biomass = np.empty(num_timesteps)
    for timestep in range(num_timesteps):
        total_biomass[timestep] = sum(
                [biomass[timestep] for biomass in biomass_data.values()])
    return total_biomass

def net_production(species_data, node_config, biomass_data):
    """
    Time-series measure of ecosystem health
    computed as net production (change/derivative in total biomass)
    """
    B = total_biomass(species_data, node_config, biomass_data)
    net_prod = B - np.roll(B, 1)
    
    # Can't really say that net production was equal to total biomass at t0
    net_prod[0] = net_prod[-1] = 0
    
    return net_prod

def shannon_index_biomass_product(species_data, node_config, biomass_data):
    """
    Time-series measure of ecosystem health
    computed as the product of the Shannon index (based on biomass)
    and the total biomass.
    """
    num_timesteps = len(biomass_data[node_config[0]['nodeId']])
    scores = np.zeros(num_timesteps)
    
    for timestep in range(num_timesteps):
        species_biomass = np.empty(len(node_config))
        for i, node in enumerate(node_config):
            species_biomass[i] = max(0, biomass_data[node['nodeId']][timestep])
        total_biomass = species_biomass.sum()
        for i, node in enumerate(node_config):
            if species_biomass[i] <= 0:
                continue
            proportion = species_biomass[i] / total_biomass
            scores[timestep] -= proportion * log2(proportion)
        scores[timestep] *= total_biomass
    
    return scores

def shannon_index_biomass_product_norm(species_data, node_config, biomass_data):
    """
    A version of shannonIndexBiomassProduct normalized by initial total biomass
    and maximum possible Shannon index for the number of species,
    enabling more meaningful comparison across ecosystems of different sizes.
    """

    total_initial_biomass = sum(
            [biomass[0] for biomass in biomass_data.values()])
    perfect_shannon = 0
    for i, node in enumerate(node_config):
        proportion = 1 / len(node_config)
        perfect_shannon -= proportion * log2(proportion)
    return (shannon_index_biomass_product(species_data, node_config, biomass_data)
            / (total_initial_biomass * perfect_shannon))

def last_nonzero_timestep(biomass_data_frame):
    """
    Returns the last timestep at which there is nonzero biomass.
    """
    df = biomass_data_frame
    nonzero = pd.Series(index=df.index, data=False)
    for col in df:
        nonzero |= (df[col] != 0)
    return nonzero.sort_index(ascending=False).argmax()

def get_output_attributes(speciesData, nodeConfig, biomass_data):
    """
    Given speciesData as returned by getSpeciesData,
    nodeConfig and biomassData as returned by get_simulation_data,
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

    # Convert biomass data to a pandas DataFrame
    # FIXME: Should use pandas throughout
    biomass_data_frame = pd.DataFrame(biomass_data)

    # Output attributes
    out = {}

    num_species = len(biomass_data)
    surviving20 = num_species
    surviving1000 = num_species
    extinction_timesteps = []

    # Store sd(log N) amplitudes for all species
    amplitudes_sd_log_n = []

    for node_id, biomass_series in biomass_data.items():
        num_timesteps = len(biomass_series)
        cumulative_biomass = 0
        cumulative_biomass2 = 0
        extinct = False
        out['extinction_' + str(node_id)] = NO_EXTINCTION
        for timestep, biomass in enumerate(biomass_series):
            if not extinct:
                if biomass == 0:
                    out['extinction_' + str(node_id)] = timestep
                    extinction_timesteps.append(timestep)
                    extinct = True
                    if timestep <= 20:
                        surviving20 -= 1
                    if timestep <= 1000:
                        surviving1000 -= 1
                else:
                    cumulative_biomass += biomass
            cumulative_biomass2 += biomass
        out['avgBiomass_' + str(node_id)] = (cumulative_biomass
                / float(num_timesteps))
        out['avgBiomass2_' + str(node_id)] = (cumulative_biomass2
                / float(num_timesteps))

        # Amplitude measured as SD(log N) (Kendall et al. 1998)
        amp = np.std(np.log10(biomass_data_frame[node_id] + 1))
        amplitudes_sd_log_n.append(amp)
        out['amplitude_sdLogN_' + str(node_id)] = amp

    out['amplitude_sdLogN_min'] = min(amplitudes_sd_log_n)
    out['amplitude_sdLogN_mean'] = sum(amplitudes_sd_log_n) / len(amplitudes_sd_log_n)
    out['amplitude_sdLogN_max'] = max(amplitudes_sd_log_n)

    out['surviving20'] = surviving20
    out['surviving1000'] = surviving1000

    #
    # Scalar measures of ecosystem health
    #

    # Average of original environment score formula
    #out['avgEcosystemScore'] = getAvgEcosystemScore(
    #        speciesData, nodeConfig, biomassData)

    t = np.arange(num_timesteps)

    # Slope of linear regression of shannonIndexBiomassProduct
    #health = shannonIndexBiomassProduct(
    #        speciesData, nodeConfig, biomassData)
    #slope, intercept, r_value, p_value, std_err = stats.linregress(
    #        t, health)
    #out['shannonBiomassSlope'] = slope

    # Slope of linear regression of shannonIndexBiomassProduct
    #health = shannonIndexBiomassProductNorm(
    #        speciesData, nodeConfig, biomassData)
    #slope, intercept, r_value, p_value, std_err = stats.linregress(
    #        t, health)
    #out['shannonBiomassNormSlope'] = slope

    # Slope of linear regression on local peaks in net production
    #netProd = netProduction(
    #        speciesData, nodeConfig, biomassData)
    # Without smoothing, there are many tiny local peaks
    #smoothedNetProd = np.convolve(netProd, np.hanning(20), mode='same')
    #maxIndices, = signal.argrelmax(smoothedNetProd)
    #maxValues = np.take(netProd, maxIndices)
    #try:
    #    out['peakNetProductionSlope'] = stats.linregress(maxIndices, maxValues)[0]
    #except ValueError:
    #    print("Warning: error calculating peak net production slope")
    #    out['peakNetProductionSlope'] = ''


    # Slope of linear regression on environment score
    scores = environment_score(speciesData, nodeConfig, biomass_data)
    #out['environmentScoreSlope'] = stats.linregress(t, scores)[0]
    # Slope of log-linear regression on environment score
    #out['environmentScoreLogSlope'] = stats.linregress(t, np.log(scores))[0]

    # Slope of linear regression on environment score starting at a later
    # time step, allowing for a settling-down period
    mean_period = 500
    for start_time, end_time in ((200, 500), (200, 1000), (200, 5000), (1000, 5000)):
        out['environmentScoreSlope_{}_{}'.format(start_time, end_time)] = \
                stats.linregress(t[start_time:end_time],
                        scores[start_time:end_time])[0]
        mean_start_time = end_time - mean_period
        out['environmentScoreMean_{}_{}'.format(mean_start_time, end_time)] = \
                scores[mean_start_time:end_time].mean()

    last_nonzero_t = last_nonzero_timestep(biomass_data_frame)
    out['timesteps'] = num_timesteps
    out['lastNonzeroTimestep'] = last_nonzero_t
    out['lastNonzeroBiomass'] = biomass_data_frame.loc[last_nonzero_t].sum()

    out['maxBiomass'] = biomass_data_frame.max().max()
    out['minBiomass'] = biomass_data_frame.min().min()

    return out


def generate_feature_file(set_number, output_file, biomass_files):
    species_data = get_species_data()

    outfile = None
    writer = None

    for sim_number, infilename in sorted(
            [(get_sim_number(f), f) for f in biomass_files]):

        # Create the output row from the simulation identifiers, input and
        # output attributes
        outrow = {}
        identifiers = {
            'filename': os.path.basename(infilename),
            'setNumber': set_number,
            'simNumber': sim_number,
        }
        outrow.update(identifiers)
        node_config, input_attributes, biomass_data = get_simulation_data(infilename)
        outrow.update(input_attributes)
        output_attributes = get_output_attributes(
            species_data, node_config, biomass_data)
        outrow.update(output_attributes)

        if writer is None:
            # Set up the CSV writer

            fieldnames = (
                list(identifiers.keys()) +
                sorted(input_attributes.keys()) +
                sorted(output_attributes.keys()))
            outfile = open(output_file, 'w')
            writer = csv.DictWriter(outfile, fieldnames)
            writer.writeheader()

        writer.writerow(outrow)

    if outfile is not None:
        outfile.close()
