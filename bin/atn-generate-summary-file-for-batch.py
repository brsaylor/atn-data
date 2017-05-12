#!/usr/bin/env python3

""" Generates a summary file for the given batch of data.
"""

import argparse

from atntools.summarize import generate_summary_file_for_batch

parser = argparse.ArgumentParser(description=globals()['__doc__'])
parser.add_argument('set_number', type=int)
parser.add_argument('batch_number', type=int)
parser.add_argument(
    '--optional',
    nargs='*',
    choices=['environment_score_slope', 'environment_score_slope_skip200'],
    help="List of optional output attributes to include")
args = parser.parse_args()

generate_summary_file_for_batch(
    args.set_number,
    args.batch_number,
    args.optional)
