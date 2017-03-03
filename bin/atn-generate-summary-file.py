#!/usr/bin/env python3

""" Generates a summary file from the given biomass data.
"""

import argparse

from atntools.summarize import generate_summary_file

parser = argparse.ArgumentParser(description=globals()['__doc__'])
parser.add_argument('set_number')
parser.add_argument('output_file', help="Summary file")
parser.add_argument('biomass_files', nargs='+', help="ATN*.h5")
args = parser.parse_args()

generate_summary_file(args.set_number, args.output_file, args.biomass_files)
