#!/usr/bin/env python3

import sys
import json

import numpy as np
import pandas as pd

import trees
from nodeconfig_generator import validParamRanges
import util

def get_ranges_for_leaf(leaf):
    """
    Get the attribute ranges corresponding a leaf in a decision tree.


    Parameters
    ----------
    leaf : trees.TreeNode
        The leaf for which to determine ranges

    Returns
    -------
    dict
        Keys are attribute names. Values are (low, high) tuples, with None for
        low or high if there is no lower/upper bound for that attribute in the
        path to the leaf.
        Example:
        {
            'X70': (0.124, 0.16275),
            'X14': (0.801, None),
            'X42': (0.60515, None),
            'X31': (None, 0.65),
            'R5': (None, 1.25)
        }
    """

    # the returned dict
    ranges = {}

    node = leaf
    parent = leaf.parent
    while parent is not None:
        attribute = parent.split_attribute
        if attribute in ranges:
            low, high = ranges[attribute]
        else:
            low, high = None, None
        if node is parent.child_gt:
            if low is None or parent.split_value > low:
                low = parent.split_value
        else: # node is parent.child_lte
            if high is None or parent.split_value < high:
                high = parent.split_value
        ranges[attribute] = (low, high)
        node = node.parent
        parent = node.parent

    return ranges

# NOTE: Not using the method, because I'm not sure it makes sense for this
# purpose
def combine_weighted_segments(in_segments):
    """
    Combine a list of weighted segments, accounting for overlap.

    Parameters
    ----------
    in_segments : iterable object
        A sequence of tuples, each in the form (start, end, weight).

    Returns
    -------
    iterable object
        A sequence of tuples, each in the form (start, end, weight), sorted by
        `start`, such that the t[i].end <= t[i+1].start for all tuples t[i] in
        the sequence (i.e. the segments do not overlap). Overlapping regions
        among the segments in `in_segments` are broken into new output segments
        with the sum of the weights of the overlapping input segments.
    """

    # re-arrange:
    # [(a1, b1, w1), (a2, b2, w2), ...]
    # becomes
    # [(a1, w1), (b1, -w1), (a2, w2), (b2, -w2)]
    delta_sequence = []
    for start, end, weight in in_segments:
        delta_sequence.append((start, weight))
        delta_sequence.append((end, -weight))

    # sort by endpoint value
    delta_sequence.sort()

    # follow the sequence of endpoints, tracking the running sum of the weight,
    # outputting a new segment each time an endpoint is encountered
    running_weight = 0
    out_segments = []
    for i in range(len(delta_sequence) - 1):
        point, weight = delta_sequence[i]
        next_point = delta_sequence[i+1][0]
        running_weight += weight
        if point != next_point:
            out_segments.append((point, next_point, running_weight))

    return out_segments

def test_combine_weighted_segments():

    # disjoint segments:
    # -- --
    in_segments =  [(1, 2, 3), (3, 4, 2)]
    out_segments = [(1, 2, 3), (2, 3, 0), (3, 4, 2)]
    assert combine_weighted_segments(in_segments) == out_segments

    # adjoining segments:
    # ----
    in_segments =  [(1, 2, 3), (2, 3, 2)]
    out_segments = [(1, 2, 3), (2, 3, 2)]
    assert combine_weighted_segments(in_segments) == out_segments

    # simple overlap:
    # ---
    #  ---
    in_segments =  [(1, 3, 3), (2, 4, 2)]
    out_segments = [(1, 2, 3), (2, 3, 5), (3, 4, 2)]
    assert combine_weighted_segments(in_segments) == out_segments

    # identical endpoints:
    # ---
    # ---
    in_segments =  [(1, 3, 1), (1, 3, 2)]
    out_segments = [(1, 3, 3)]
    assert combine_weighted_segments(in_segments) == out_segments

    # same segment overlapping on both ends:
    # ----
    #  --
    in_segments =  [(1, 4, 1), (2, 3, 2)]
    out_segments = [(1, 2, 1), (2, 3, 3), (3, 4, 1)]
    assert combine_weighted_segments(in_segments) == out_segments

    # 3-segment overlap:
    # 12345
    # ---
    #  ---
    #   ---
    in_segments =  [(1, 4, 1), (2, 5, 2), (3, 6, 3)]
    out_segments = [(1, 2, 1), (2, 3, 3), (3, 4, 6), (4, 5, 5), (5, 6, 3)]
    assert combine_weighted_segments(in_segments) == out_segments

# NOTE: Not using the method, because I'm not sure it makes sense for this
# purpose
def get_parameter_distributions(tree):
    """
    Calculate parameter distributions based on the given decision tree.

    For each parameter/attribute, a piecewise distribution is computed. Each
    segment of this distribution has two endpoints (on the 'x' axis) and a
    constant weight (on the 'y' axis'). The weight of a segment is the sum of
    the number of "good" instances within its range, minus the number of "bad"
    instances. Each leaf of the tree may contribute a segment of this
    distribution, based on the attribute split points along the path from the
    leaf to the root. 

    Parameters
    ----------
    tree : TreeNode
        The root node of the tree.

    Returns
    -------
    dict
        key: parameter name
        value: list of non-overlapping weighted segments, each one of which is a
               tuple in the form (low, high, weight)
    """

    # upper and lower limits for parameter ranges
    # key: parameter name
    # value: (low, high)
    limits = {}

    # Assemble the parameter ranges for each leaf into a list of weighted
    # segments for each parameter.
    # key: parameter name
    # value: list of (low, high, weight) segments for the parameter
    segments = {}

    for leaf in tree.get_leaves():
        weight = leaf.instance_count - leaf.misclassified_count
        if leaf.class_label == 'bad':
            weight = -weight

        for param, (low, high) in get_ranges_for_leaf(leaf).items():

            # Ranges can have None for low or high, if there is no lower or
            # upper bound, respectively. Replace None with the lowest or highest
            # valid value for the parameter.
            if param not in limits:
                param_base_name = util.remove_trailing_digits(param)
                limits[param] = validParamRanges[param_base_name]
            low = low or limits[param][0]
            high = high or limits[param][1]
            
            seg = (low, high, weight)
            if param not in segments:
                segments[param] = [seg]
            else:
                segments[param].append(seg)

    # For each parameter, combine the weighted segments.
    # key: parameter name
    # value: list of combined segments for the parameter, none overlapping
    combined_segments = {}
    for param, param_segments in segments.items():
        combined_segments[param] = combine_weighted_segments(segments[param])

    return combined_segments

def get_distributions(tree, instances):
    """
    Calculate piecewise distributions of good, bad, and unlabeled instances.

    Parameters
    ----------
    tree : TreeNode
        The decision tree.
    instances : DataFrame
        Labeled instances used to train the decision tree. Must have a column
        for each attribute in the tree, and a 'label' column with values 'good',
        'bad', or NaN (unlabeled).

    Returns
    -------
    dict
        key: parameter name
        value: list of tuples, each of which describes a range of values for the
        parameter, delimited by a pair of split points in the tree:
        (high, low, good_count, bad_count, unlabeled_count)
    """
    
    # key: parameter name
    # value: list of split values
    splits = {}
    for node in tree.get_internal_nodes():
        if node.split_attribute not in splits:
            splits[node.split_attribute] = [node.split_value]
        else:
            splits[node.split_attribute].append(node.split_value)
    
    # key: parameter name
    # value: list of tuples: (high, low, good_count, bad_count, unlabeled_count)
    distributions = {}
    for param, split_values in splits.items():
        split_values.sort()
        param_base_name = util.remove_trailing_digits(param)
        min_valid_value, max_valid_value = validParamRanges[param_base_name]
        split_values.insert(0, min_valid_value)
        split_values.append(max_valid_value)

        # FIXME: There must be a more efficient way to use pandas for this
        df = instances
        segments = []
        for i in range(len(split_values) - 1):
            low = split_values[i]
            high = split_values[i+1]
            df2 = df[(df[param] > low) & (df[param] <= high)]
            counts = df2['label'].value_counts(dropna=False)
            segments.append((low, high,
                int(counts.loc['good']),
                int(counts.loc['bad']),
                int(counts.loc[np.nan])))

        distributions[param] = segments

    return distributions

def get_range_weights(distributions):
    """
    Calculate scoring weights for each range in the given parameter ranges.

    The weight for a range is defined as P(good) - P(bad), with the denominator
    of the probabilities being the total number of instances (labeled and
    unlabeled) in the range.

    Parameters
    ----------
    distributions : dict
        Piecewise distributions as returned by get_distributions().

    Returns
    -------
    dict
        key: parameter name
        value: list of tuples in the form (low, high, weight)
    """

    # the returned dict
    range_weights = {}

    for param, in_segments in distributions.items():
        out_segments = []
        for low, high, good, bad, unlabeled in in_segments:
            weight = (good - bad) / (good + bad + unlabeled)
            out_segments.append((low, high, weight))
        range_weights[param] = out_segments

    return range_weights

if __name__ == '__main__':

    #test_combine_weighted_segments()
    #sys.exit(0)
    
    if len(sys.argv) != 3:
        print("Usage: ./tree_ranges.py weka-J48-output-file.txt labeled-feature-file.csv")
        sys.exit(1)
    tree = trees.parse_weka_j48_output_file(sys.argv[1])
    instances = pd.read_csv(sys.argv[2])
    distributions = get_distributions(tree, instances)
    range_weights = get_range_weights(distributions)

    print("\nDISTRIBUTIONS:\n")
    print(json.dumps(distributions, sort_keys=True, indent=4))
    print("\nRANGE WEIGHTS:\n")
    print(json.dumps(range_weights, sort_keys=True, indent=4))

    #print("Ranges:")
    #for leaf in tree.get_leaves():
    #    print(str(leaf))
    #    json.dump(get_ranges_for_leaf(leaf),
    #            sys.stdout, sort_keys=True, indent=4)
    #    print("\n")
