#!/usr/bin/env python3

""" Generates a plot and JSON file describing a food web.

Files are stored in a directory named based on the species in the food web.

If --parent-dir is not specified, the parent directory is determined
automatically based on DATA_HOME.
"""

import os
import sys
import argparse

from atntools import settings
from atntools import foodwebs
from atntools import util

parser = argparse.ArgumentParser(description=globals()['__doc__'])
parser.add_argument('--parent-dir', help="Parent directory to use instead of automatically-determined directory under DATA_HOME")
subparsers = parser.add_subparsers(dest='subparser_name')

# 'generate' sub-command
parser_generate = subparsers.add_parser('generate', help="Generate a new food web and save plot and JSON")
parser_generate.add_argument('size', type=int, help="Number of species")
parser_generate.add_argument('num_basal_species', type=int, help="Number of basal species")

# 'regenerate' sub-command
parser_regenerate = subparsers.add_parser('regenerate', help="Regenerate files in existing food web directory")
parser_regenerate.add_argument('existing_dir', help="Existing food web directory")

# 'from-node-ids' sub-command
parser_from_node_ids = subparsers.add_parser('from-node-ids', help="Generate plot and JSON from given node IDs")
parser_from_node_ids.add_argument('node_ids', nargs='+', type=int, help="List of node IDs")

args = parser.parse_args()

if not args.subparser_name:
    # No sub-command given
    parser.print_usage()
    sys.exit(1)

if args.subparser_name == 'generate':

    subweb = foodwebs.serengeti_predator_complete_subweb(args.size, args.num_basal_species)
    node_ids = sorted(subweb.nodes())
    food_web_id = '-'.join([str(x) for x in node_ids])
    if args.parent_dir is None:
        food_web_dir = util.get_food_web_dir(food_web_id)
    else:
        food_web_dir = os.path.join(os.path.expanduser(args.parent_dir), food_web_id)
    print("Creating food web directory " + food_web_dir)
    os.makedirs(food_web_dir)

elif args.subparser_name == 'regenerate':

    food_web_dir = os.path.normpath(args.existing_dir)
    if not os.path.isdir(food_web_dir):
        print("Error: directory doesn't exist: " + food_web_dir, file=sys.stderr)
        sys.exit(1)
    food_web_id = os.path.basename(food_web_dir)
    node_ids = [int(x) for x in food_web_id.split('-')]
    serengeti = foodwebs.read_serengeti()
    subweb = serengeti.subgraph(node_ids)

elif args.subparser_name == 'from-node-ids':

    node_ids = sorted(args.node_ids)
    serengeti = foodwebs.read_serengeti()
    subweb = serengeti.subgraph(node_ids)
    food_web_id = '-'.join([str(x) for x in node_ids])
    if args.parent_dir is None:
        food_web_dir = util.get_food_web_dir(food_web_id)
    else:
        food_web_dir = os.path.join(os.path.expanduser(args.parent_dir), food_web_id)
    print("Creating food web directory " + food_web_dir)
    os.makedirs(food_web_dir)

foodwebs.draw_food_web(subweb, show_legend=True,
                       output_file=os.path.join(food_web_dir, 'foodweb.{}.png'.format(food_web_id)))

with open(os.path.join(food_web_dir, 'foodweb.{}.json'.format(food_web_id)), 'w') as f:
    print(foodwebs.food_web_json(subweb), file=f)
