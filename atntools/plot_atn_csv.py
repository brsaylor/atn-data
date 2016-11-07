#!/usr/bin/env python3

# Ben Saylor
# October 2015

"""
Plot a CSV output by ATNEngine
"""

import sys
import os
import csv
import re
import json
import gzip
import argparse

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
from scipy import stats, signal
import pandas as pd

from atntools.features import get_species_data, get_simulation_data, environment_score
from atntools.nodeconfigs import parse_node_config

species_data = None


def plot_csv(filename, score_function, show_legend=False, figsize=None, output_file=None, xlim=None, ylim=None):
    """ Plot the given biomass CSV file produced by WoB Server.

    Parameters
    ----------
    filename : str
        CSV filename (may be gzipped)
    score_function : callable
        Function of species_data, node_config, biomass_data returning an ndarray
    show_legend : bool
        If True, include legend in plot
    figsize : tuple
        Figure size passed to plt.subplots()
    output_file : str
        Name of output file to save (if None, no output file will be created)
    xlim : tuple
        x-axis limits (xmin, xmax)
    ylim : tuple
        y-axis limits (ymin, ymax)
    """
    global species_data
    if species_data is None:
        species_data = get_species_data()

    node_config, node_config_attributes, biomass_data = get_simulation_data(filename)
    
    if figsize is not None:
        fig, ax1 = plt.subplots(figsize=figsize)
    else:
        fig, ax1 = plt.subplots()
    ax1.set_xlabel("timestep")
    ax1.set_ylabel("biomass")

    # Set x-axis and y-axis limits if requested
    if xlim:
        plt.xlim(xlim)
    if ylim:
        plt.ylim(ylim)

    legend = []
    for node_id, series in sorted(biomass_data.items()):
        plt.plot(biomass_data[node_id])
        legend.append("[{}] {}".format(node_id, species_data[node_id]['name']))
    if show_legend:
        lgd = ax1.legend(legend, bbox_to_anchor=(1.05, 1), loc=2, borderaxespad=0.)

    if score_function and node_config:
        scores = score_function(species_data, node_config, biomass_data)
        ax2 = ax1.twinx()
        ax2.plot(scores, linewidth=2)
        #ax2.legend(['score'])  # gets drawn on top of main legend
        ax2.set_ylabel("score")

        # Linear regression
        t = np.arange(len(scores))
        tn = len(scores) - 1
        slope, intercept, r_value, p_value, std_err = stats.linregress(
                t, scores)
        #ax2.plot([0, tn], [intercept, slope * tn + intercept], 'g', linewidth=2)

        # Linear regression, but starting at timestep 200
        #startTime = 400
        #slope, intercept, r_value, p_value, std_err = stats.linregress(
        #        t[startTime:], scores[startTime:])
        #ax2.plot([0, tn], [intercept, slope * tn + intercept], 'b', linewidth=2)

        # Log-linear regression
        log_slope, log_intercept, r_value, p_value, std_err = stats.linregress(
                t, np.log(scores))
        #ax2.plot(t, np.e**(log_slope*t + log_intercept))

        # Regions between local "maxima" (may be plateaus due to rounding)
        # To round off plateaus, do some smoothing by convolving with a Hanning
        # window
        smoothed = np.convolve(scores, np.hanning(20), mode='same')
        max_indices, = signal.argrelmax(smoothed)
        max_values = np.take(scores, max_indices)
        #ax2.plot(maxIndices, maxValues, 'r^')
        #
        regions = np.split(scores, max_indices)
        region_averages = [region.mean() for region in regions]
        region_centers = np.empty(len(regions))
        tprev = 0
        for i, t in enumerate(max_indices):
            region_centers[i] = (tprev + t) / 2
            tprev = t
        region_centers[-1] = (tprev + len(scores)) / 2
        #ax2.plot(regionCenters, regionAverages, 'ro')

        # Linear regression on local maxima
        #mSlope, mIntercept, r_value, p_value, std_err = stats.linregress(
        #        maxIndices, maxValues)
        #ax2.plot([0, tn], [mIntercept, mSlope * tn + mIntercept], 'g:')

        # Log-linear regression on local maxima
        #mLogSlope, mLogIntercept, r_value, p_value, std_err = stats.linregress(
        #        maxIndices, np.log(maxValues))
        t = np.arange(len(scores))
        #ax2.plot(t, np.e**(mLogSlope*t + mLogIntercept), 'r:')

    plt.title(filename)

    if output_file:
        dpi=200
        if show_legend:
            plt.savefig(output_file, bbox_extra_artists=(lgd,),
                        bbox_inches='tight', dpi=dpi)
        else:
            plt.savefig(output_file, dpi=dpi)
    else:
        plt.show()

    return

    # FIXME: need a better way to retrieve/display this info
    print("TREND MEASURES:")
    print("sum of derivative: {}".format(sum_derivative(scores)))
    print("linear regression: slope = {}, intercept = {}".format(
        slope, intercept))
    print("log-linear regression: slope = {}, intercept = {}".format(
        log_slope, log_intercept))
    print("linear regression of peaks: slope = {}, intercept = {}".format(
        mSlope, mIntercept))
    print("log-linear regression of peaks: slope = {}, intercept = {}".format(
        mLogSlope, mLogIntercept))
    print("regionAverages[-2] - regionAverages[1] = {}".format(
        region_averages[-2] - region_averages[1]))
    print("regionAverages[-2] / regionAverages[1] = {}".format(
        region_averages[-2] / region_averages[1]))
    print("average (excluding first timestep): {}".format(
        scores[1:].mean()))

    print("\nSPECIES DATA:")
    print_species_data(species_data, node_config)


def print_species_data(species_data, node_config):
    """
    Print out a formatted JSON representation of the node config and
    species-level data
    """
    dataByNodeId = {}
    for node in node_config:
        nodeId = node['nodeId']
        data = {}
        data.update(node)
        data.update(species_data[nodeId])
        dataByNodeId[nodeId] = data
    print(json.dumps(dataByNodeId, indent=4, sort_keys=True))

def plot_top_bottom_n(n, biomass_dir, feature_file, ranking_col, output_dir):
    if output_dir is None:
        output_dir = '.'

    feature_data = pd.read_csv(args.feature_file)

    if ranking_col not in feature_data:
        print("Error: {} does not have a column named {}".format(
            feature_file, ranking_col), file=sys.stderr)
        sys.exit(1)

    os.makedirs(output_dir, exist_ok=True)

    ranked_filenames = feature_data.sort_values(ranking_col,
            ascending=False)['filename']

    def save_plot(rank, filename):
        """
        Plot the given file and save to an image file.
        rank: 1-based rank in terms of ranking_col
        filename: basename of gzipped biomass CSV
        """
        input_file = os.path.join(biomass_dir, filename)
        output_file = os.path.join(output_dir, 'rank_{}_{}'.format(
            rank, filename.replace('.csv.gz', '.png')))
        plot_csv(input_file, environment_score, show_legend=True, output_file=output_file)

    for rank, filename in enumerate(ranked_filenames[:n], start=1):
        save_plot(rank, filename)

    for rank, filename in enumerate(ranked_filenames[-n:],
            start=len(ranked_filenames)-n+1):
        save_plot(rank, filename)

# FIXME: Refactoring needed
def sum_derivative(series):
    # Note: sum of finite-difference derivative is last value minus first
    # value
    return series[-1] - series[0]

if __name__ == '__main__':

    parser = argparse.ArgumentParser()
    parser.add_argument('--top-bottom-n', type=int,
            help="Plot the top and bottom N simulations")
    parser.add_argument('--biomass-dir',
            help="Path to biomass CSV files")
    parser.add_argument('--feature-file',
            help="Path to feature file")
    parser.add_argument('--ranking-col',
            help="Feature file column to use for ranking simulations")
    parser.add_argument('--output-dir',
            help="Output directory for PNG images")
    args = parser.parse_args()

    if args.top_bottom_n:
        if not os.path.isdir(args.biomass_dir or ''):
            print("Error: {} is not a directory".format(args.biomass_dir),
                    file=sys.stderr)
            sys.exit(1)
        if not os.path.isfile(args.feature_file or ''):
            print("Error: {} not found".format(args.feature_file),
                    file=sys.stderr)
            sys.exit(1)

        # FIXME: Better way to have conditionally required args with argparse?
        if args.ranking_col is None:
            print("Error: --ranking_col is required", file=sys.stderr)
            sys.exit(1)

        plot_top_bottom_n(args.top_bottom_n, args.biomass_dir,
                args.feature_file, args.ranking_col,
                os.path.expanduser(args.output_dir))

    else:
        # Default operation

        filenames = sys.argv[1:]
        for filename in filenames:
            plot_csv(filename)
