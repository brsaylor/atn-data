#!/usr/bin/env python3

""" Runs the node config generator with the given set number. """

import sys
import argparse

from atntools import nodeconfigs

#parser = argparse.ArgumentParser(description=globals()['__doc__'])
#parser.add_argument('set_number', type=int)
#args = parser.parse_args()

for node_config in nodeconfigs.generate_uniform(
        [2, 15, 17, 22, 26],
        {
            'initialBiomass': [100, 5000],
            'X': [0, 1],
            'R': 1,
            'K': [1000, 15000],
        },
        10):
    print(node_config)
