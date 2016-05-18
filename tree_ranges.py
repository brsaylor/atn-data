#!/usr/bin/env python3

import sys
import json

import trees

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

if __name__ == '__main__':

    test_combine_weighted_segments()
    sys.exit(0)
    
    if len(sys.argv) != 2:
        print("Usage: ./tree_ranges.py weka-J48-output-file.txt")
        sys.exit(1)
    tree = trees.parse_weka_j48_output_file(sys.argv[1])
    print(str(tree))
    print()
    print("Ranges:")
    for leaf in tree.get_leaves():
        print(str(leaf))
        json.dump(get_ranges_for_leaf(leaf),
                sys.stdout, sort_keys=True, indent=4)
        print("\n")
