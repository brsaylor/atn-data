#!/usr/bin/env python3

""" Generates parameter ranges from J48 trees, outputs plots and JSON files.
"""

import os
import sys
import argparse

from atntools.tree_range_plots import plot_tree_ranges

parser = argparse.ArgumentParser(description=globals()['__doc__'])
parser.add_argument('tree_file', help="Weka J48 output file")
parser.add_argument('feature_file', help="Labeled feature file")
parser.add_argument('output_dir', help="Output directory for plot and json")
args = parser.parse_args()

if not os.path.isfile(args.tree_file):
    print("Error: {}: no such file".format(args.tree_file))
    sys.exit(1)

if not os.path.isfile(args.feature_file):
    print("Error: {}: no such file".format(args.feature_file))
    sys.exit(1)

plot_tree_ranges(args.tree_file, args.feature_file, args.output_dir)
