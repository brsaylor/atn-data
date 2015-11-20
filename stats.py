#!/usr/bin/env python3

import sys

import pandas as pd
import numpy as np

pd.set_option('display.max_columns', 999)
pd.set_option('display.max_rows', 999)

for filename in sys.argv[1:]:

    print("===================================================================")
    print(filename)
    print("-------------------------------------------------------------------")

    df = pd.read_csv(filename)
    values = [s for s in list(df.columns)
            if not s == 'classification'
            and not s.startswith('perUnitBiomass')
            and not s.startswith('extinction')]

    df['classification'] = df['classification'].astype("category")
    df['classification'].cat.set_categories(['good', 'bad'], inplace=True)

    table = pd.pivot_table(df, index=['classification'], values=values[:1],
            aggfunc=[len])
    print(table.T)
    table = pd.pivot_table(df, index=['classification'], values=values,
            aggfunc=[np.mean, np.std, np.median])
    print(table.T)
    print()
