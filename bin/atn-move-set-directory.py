#!/usr/bin/env python3

"""
Move a set directory to the proper place under the root directory
depending on the number of species and the food web ID.
"""

import os
import sys
import argparse

from atntools.nodeconfig_generator import parse_node_config

parser = argparse.ArgumentParser(description=globals()['__doc__'])
parser.add_argument('set_directory', help="Directory containing the set (i.e. set999)")
parser.add_argument('data_directory', help="Data root directory")
args = parser.parse_args()

# Check for set directory and data directory
if not os.path.isdir(args.set_directory):
    print("Error: set directory {} does not exist".format(args.set_directory), file=sys.stderr)
    sys.exit(1)
if not os.path.isdir(args.data_directory):
    print("Error: data directory {} does not exist".format(args.data_directory), file=sys.stderr)
    sys.exit(1)
set_directory = os.path.normpath(args.set_directory)
data_directory = os.path.normpath(args.data_directory)

# Read the first nodeconfig from the nodeconfig file in the set directory
nodeconfig_filename = os.path.join(set_directory, 'nodeconfigs.{}.txt'.format(os.path.basename(set_directory)))
try:
    nodeconfig_file = open(nodeconfig_filename)
except IOError:
    print("Error: could not read node config file {}".format(nodeconfig_filename), file=sys.stderr)
    sys.exit(1)
nodeconfig_str = nodeconfig_file.readline()
nodeconfig_file.close()
nodeconfig = parse_node_config(nodeconfig_str)

# Determine the number of species and food web ID
node_ids = [node['nodeId'] for node in nodeconfig]
node_ids.sort()
num_species = len(node_ids)
food_web_id = '-'.join(map(str, node_ids))

# Do the move
new_set_directory = os.path.join(data_directory, '{}-species'.format(num_species), food_web_id, set_directory)
print("Moving {} to {}".format(set_directory, new_set_directory))
os.renames(set_directory, new_set_directory)
