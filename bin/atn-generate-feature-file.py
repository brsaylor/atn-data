#!/usr/bin/env python3

""" Generates a feature file from the given biomass data.
"""

import argparse

from atntools.features import generate_feature_file

parser = argparse.ArgumentParser(description=globals()['__doc__'])
parser.add_argument('set_number')
parser.add_argument('output_file', help="Feature file")
parser.add_argument('biomass_files', nargs='+', help="ATN*.csv.gz")
args = parser.parse_args()

generate_feature_file(args.set_number, args.output_file, args.biomass_files)