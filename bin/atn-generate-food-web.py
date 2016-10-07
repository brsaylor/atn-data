#!/usr/bin/env python3

import os
import sys
import argparse

from atntools import foodwebs

parser = argparse.ArgumentParser()
parser.add_argument('--existing-dir', help="Existing food web directory to use")
args = parser.parse_args()
if args.existing_dir is None:
    print("--existing-dir is required for now", file=sys.stderr)
    sys.exit(1)

food_web_id = os.path.basename(os.path.normpath(args.existing_dir))

node_ids = [int(x) for x in food_web_id.split('-')]

serengeti = foodwebs.read_serengeti()
subweb = serengeti.subgraph(node_ids)

foodwebs.draw_food_web(subweb, show_legend=True,
    output_file=os.path.join(args.existing_dir, 'foodweb.{}.png'.format(food_web_id)))

with open(os.path.join(args.existing_dir, 'foodweb.{}.json'.format(food_web_id)), 'w') as f:
    print(foodwebs.food_web_json(subweb), file=f)
