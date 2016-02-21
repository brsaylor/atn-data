#!/usr/bin/env python3

import sys

import pandas as pd

def assign_labels(df):
    col = 'environmentScoreSlope' 
    q1 = df[col].quantile(0.25)
    q4 = df[col].quantile(0.75)
    print('first quartile = {}, last quartile = {}'.format(q1, q4))
    df.loc[df[col] <= q1, 'label'] = 'bad'
    df.loc[df[col] >= q4, 'label'] = 'good'

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

    # Assign labels
    assign_labels(df)
    
    # Save the result
    df.to_csv(outfilename, index=False)
