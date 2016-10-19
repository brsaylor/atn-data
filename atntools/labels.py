#!/usr/bin/env python3

import sys

import pandas as pd

# Used to identify instances of misbehaving ATNEngine
MAX_REASONABLE_BIOMASS = 100000
MAX_REASONABLE_LAST_NONZERO_BIOMASS = 100


def remove_ugly_instances(df):
    """ Return a new DataFrame with "ugly" instances removed (misbehaving
    ATNEngine causing biomass to explode and/or crash to zero) """
    df2 = df[(
                # Final timestep is nonzero,
                # or final nonzero value is small enough that it wasn't a crash
                (df.lastNonzeroTimestep == df.timesteps - 1) |
                (df.lastNonzeroBiomass <= MAX_REASONABLE_LAST_NONZERO_BIOMASS)
            ) &
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

