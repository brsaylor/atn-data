#!/usr/bin/env python3

""" Generates a plot and JSON file describing a food web.

The output directory is determined automatically based on DATA_HOME and
the species in the food web.
"""

import os
import sys
import argparse

from atntools import settings
from atntools import foodwebs

parser = argparse.ArgumentParser(description=globals()['__doc__'])
subparsers = parser.add_subparsers(dest='subparser_name')

# 'generate' sub-command
parser_generate = subparsers.add_parser('generate', help="Generate a new food web and save plot and JSON")
parser_generate.add_argument('size', type=int, help="Number of species")
parser_generate.add_argument('num_basal_species', type=int, help="Number of basal species")

# 'regenerate' sub-command
parser_regenerate = subparsers.add_parser('regenerate', help="Regenerate files in existing food web directory")
parser_regenerate.add_argument('existing_dir', help="Existing food web directory")

args = parser.parse_args()

if not args.subparser_name:
    # No sub-command given
    parser.print_usage()
    sys.exit(1)

if args.subparser_name == 'generate':

    subweb = foodwebs.serengeti_predator_complete_subweb(args.size, args.num_basal_species)
    node_ids = sorted(subweb.nodes())
    food_web_id = '-'.join([str(x) for x in node_ids])
    food_web_dir = os.path.join(settings.DATA_HOME, '{}-species'.format(args.size), food_web_id)
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

foodwebs.draw_food_web(subweb, show_legend=True,
                       output_file=os.path.join(food_web_dir, 'foodweb.{}.png'.format(food_web_id)))

with open(os.path.join(food_web_dir, 'foodweb.{}.json'.format(food_web_id)), 'w') as f:
    print(foodwebs.food_web_json(subweb), file=f)
