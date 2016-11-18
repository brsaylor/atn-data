#!/usr/bin/env python3

""" Runs the node config generator with the given metaparameter JSON file. """

import sys
import argparse

from atntools import nodeconfigs

parser = argparse.ArgumentParser(description=globals()['__doc__'])
parser.add_argument('metaparameter_file')
args = parser.parse_args()

generator = nodeconfigs.generate_node_configs_from_metaparameter_file(args.metaparameter_file)
if generator is None:
    print("Error processing metaparameter file", file=sys.stderr)
    sys.exit(1)

for node_config in generator:
    print(node_config)