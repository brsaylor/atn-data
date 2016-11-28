#!/usr/bin/env python3

""" Creates and initializes a set directory for the given food web. """

import argparse
import json

from atntools import util

parser = argparse.ArgumentParser(description=globals()['__doc__'])
parser.add_argument('food_web_id', help="Food web ID (e.g. 2-15-17-22-26) (directory must exist under DATA_HOME)")
parser.add_argument('metaparameter_template', help="Template for metaparameters.json")
args = parser.parse_args()

with open(args.metaparameter_template) as f:
    metaparameter_template = json.load(f)

set_num, set_dir = util.create_set_dir(args.food_web_id, metaparameter_template)

print("Initialized set directory " + set_dir)