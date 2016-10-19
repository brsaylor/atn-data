#!/usr/bin/env python3

""" Generates a labeled feature file from the given feature file(s).
"""

import argparse

import pandas as pd

from atntools.labels import remove_ugly_instances, assign_labels

parser = argparse.ArgumentParser(description=globals()['__doc__'])
parser.add_argument('input_files', nargs='+', help="Unlabeled feature file(s)")
parser.add_argument('output_file', help="Labeled feature file (output)")
args = parser.parse_args()

# Read the input files into DataFrame df
df = None
for fname in args.input_files:
    if df is None:
        df = pd.read_csv(fname)
        columns = df.columns  # For fixing column order later
    else:
        df = df.append(pd.read_csv(fname))

# Order columns according to the first CSV
df = df[columns]

df = remove_ugly_instances(df)

# Assign labels based on environment score slope features
for col in df.columns:
    if col.startswith('environmentScoreSlope'):
        assign_labels(df, col)

# Save the result
df.to_csv(args.output_file, index=False)
