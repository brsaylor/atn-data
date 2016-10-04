#!/usr/bin/env python3

"""
Determine "good" ranges for parameters based on EM clustering of top 25% of
simulations
"""

import sys

from nodeconfig_generator import parseNodeConfig
from weka_em import parse_weka_em_output

def get_range_for_parameter(clusters, node_id, param):
    """
    Derive a range of "good" values for a parameter based on an EM-GMM
    clustering of 'good' simulations. The bottom of the range is the minimum
    (mean - stdev) for the parameter, and the top of each range is the maximum
    (mean + stdev).
    clusters: output of parse_weka_em_output
    """
    param_range = [-1, -1]
    for cluster in clusters:
        mean = cluster['nodes'][node_id][param]['mean']
        std_dev = cluster['nodes'][node_id][param]['stdDev']
        rmin = mean - std_dev
        rmax = mean + std_dev
        if param_range[0] == -1 or rmin < param_range[0]:
            param_range[0] = rmin
        if param_range[1] == -1 or rmax > param_range[1]:
            param_range[1] = rmax

    # The preferred location text file values fall within the ranges for each type of parameter:
    # X:  0 -> 1
    # K: 1000 -> 15000
    # R: 0 -> 3
    if param_range[0] < 0 or param == 'K' and param_range[0] <= 1000:
        param_range[0] = -1
    if (
            (param == 'X' and param_range[1] >= 1) or
            (param == 'K' and param_range[1] >= 15000) or
            (param == 'R' and param_range[1] >= 3)):
        param_range[1] = -1

    return param_range

def print_param_ranges(node_config, trimmed_weka_output_filename, num_clusters):
    nodes = parse_node_config(node_config)
    weka_output = ''
    with open(trimmed_weka_output_filename) as f:
        weka_output = f.read()
    
    # we don't actually use the priors, but parseWekaOutput() needs them and
    # doesn't determine the number of clusters itself
    priors = [0] * num_clusters

    clusters = parse_weka_em_output(priors, weka_output)

    range_values = []
    for node in nodes:
        if 'K' in node:
            param_range = get_range_for_parameter(clusters, node['nodeId'], 'K')
            range_values.extend(param_range)
        else:
            param_range = get_range_for_parameter(clusters, node['nodeId'], 'X')
            range_values.extend(param_range)
    print(','.join(map(str, range_values)))

if __name__ == '__main__':
    if len(sys.argv) < 4:
        print("Usage: ./parameter_ranges.py <nodeconfig> <trimmed-weka-EM-output-file> <num-clusters>")
        sys.exit(1)

    print_param_ranges(sys.argv[1], sys.argv[2], int(sys.argv[3]))
