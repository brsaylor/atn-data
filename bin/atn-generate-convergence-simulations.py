#!/usr/bin/env python3

""" Runs a sequence of simulations to generate ecosystems for Convergence. """

import argparse
import json

from atntools import convergenceprocess

parser = argparse.ArgumentParser(description=globals()['__doc__'])
parser.add_argument(
    'food_web_id',
    help="Food web ID (e.g. 2-15-17-22-26) (directory must exist under DATA_HOME)")
parser.add_argument(
    'initial_metaparameter_template',
    help="Metaparameter template file for initial set")
parser.add_argument(
    'cvg_metaparameter_template',
    help="Metaparameter template file for convergence set")
args = parser.parse_args()

with open(args.initial_metaparameter_template) as f:
    initial_metaparameter_template = json.load(f)
with open(args.cvg_metaparameter_template) as f:
    cvg_metaparameter_template = json.load(f)

convergenceprocess.run_sequence(
    args.food_web_id,
    initial_metaparameter_template,
    cvg_metaparameter_template)
