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

if __name__ == '__main__':
    
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
