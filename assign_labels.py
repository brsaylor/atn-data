#!/usr/bin/env python3

import sys

import pandas as pd

# Used to identify instances of misbehaving ATNEngine
MAX_REASONABLE_BIOMASS = 100000
MIN_REASONABLE_NONZERO_TIMESTEP = 500

def remove_ugly_instances(df):
    """ Return a new DataFrame with "ugly" instances removed (misbehaving
    ATNEngine causing biomass to explode and/or crash to zero) """
    df2 = df[(df.lastNonzeroTimestep >= MIN_REASONABLE_NONZERO_TIMESTEP) &
            (df.maxBiomass <= MAX_REASONABLE_BIOMASS)]
    total = len(df)
    ugly = total - len(df2)
    print("Removed {} badly behaved instances out of {} total ({:.2f}%)".format(
        ugly, total, 100 * (ugly / total)))
    return df2

def assign_labels(df, col):
    q1 = df[col].quantile(0.25)
    q2 = df[col].quantile(0.75)
    df.loc[df[col] <= q1, 'label_' + col] = 'bad'
    df.loc[df[col] >= q2, 'label_' + col] = 'good'

if __name__ == '__main__':
    if len(sys.argv) < 3:
        print("Usage: assign_labels.py in1.csv [in2.csv ...] out.csv")
        sys.exit(1)

    infilenames = sys.argv[1:-1]
    outfilename = sys.argv[-1]

    # Read the input files into DataFrame df
    df = None
    for fname in infilenames:
        if df is None:
            df = pd.read_csv(fname)
            columns = df.columns  # For fixing column order later
        else:
            df = df.append(pd.read_csv(fname))

    # Order columns according to the first CSV
    df = df[columns]

    df = remove_ugly_instances(df)

    # Assign labels
    for col in df.columns:
        if col.startswith('environmentScore'):
            assign_labels(df, col)
    
    # Save the result
    df.to_csv(outfilename, index=False)
