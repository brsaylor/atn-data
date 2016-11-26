#!/usr/bin/env python3

""" Runs the node config generator with the given metaparameter JSON file. """

import sys
import argparse

from atntools import nodeconfigs

parser = argparse.ArgumentParser(description=globals()['__doc__'])
parser.add_argument('metaparameter_file', help="metaparameter JSON file")
parser.add_argument('output_file', help="output file")
parser.add_argument('-w', '--food-web-file', help="food web JSON file; overrides node IDs in metaparameter file")
args = parser.parse_args()

generator = nodeconfigs.generate_node_configs_from_metaparameter_file(args.metaparameter_file, args.food_web_file)
if generator is None:
    print("Error processing metaparameter file", file=sys.stderr)
    sys.exit(1)

with open(args.output_file, 'w') as f:
    for node_config in generator:
        print(node_config, file=f)