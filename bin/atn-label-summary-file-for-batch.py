#!/usr/bin/env python3

""" Label simulations in a summary file as 'good' or 'bad' based on the quartiles
of a given column. The bottom 25% are 'bad', top 25% are good.
Used for parameter range hints (section "Identifying parameter range hints for the
Convergence game" from my thesis. """

import os.path
import argparse

import pandas as pd

from atntools import util

parser = argparse.ArgumentParser(description=globals()['__doc__'])
parser.add_argument('set_number', type=int)
parser.add_argument('batch_number', type=int)
parser.add_argument('measure_col')
parser.add_argument('bad_threshold', type=float)
parser.add_argument('good_threshold', type=float)
args = parser.parse_args()

# Read summary file
batch_dir = util.find_batch_dir(args.set_number, args.batch_number)
summary_file = os.path.join(batch_dir, 'summary.csv')
df = pd.read_csv(summary_file)

# Assign labels based on assigned threshold
df.loc[df[args.measure_col] <= args.bad_threshold, 'label'] = 'bad'
df.loc[df[args.measure_col] >= args.good_threshold, 'label'] = 'good'

# Save labeled summary file
labeled_summary_file = os.path.join(batch_dir, 'summary-labeled.csv')
df.to_csv(labeled_summary_file)
