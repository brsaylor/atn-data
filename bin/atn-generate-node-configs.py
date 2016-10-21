#!/usr/bin/env python3

""" Runs the node config generator with the given set number. """

import sys
import argparse

from atntools.nodeconfigs import generator_functions

parser = argparse.ArgumentParser(description=globals()['__doc__'])
parser.add_argument('set_number', type=int)
args = parser.parse_args()

if args.set_number not in generator_functions:
    print("Invalid set number (valid set numbers: {})".format(
        ' '.join(map(str, generator_functions.keys()))),
        file=sys.stderr)
    sys.exit(1)

generator_functions[args.set_number]()
