#!/usr/bin/env python3

""" Runs a batch of simulations for a given set. """

import argparse
import copy

from atntools import simulation

parser = argparse.ArgumentParser(description=globals()['__doc__'])
parser.add_argument('set_number', type=int, help="Set number (set directory must exist under DATA_HOME)")
parser.add_argument('timesteps', type=int, help="Number of time steps to run the simulations")
parser.add_argument('--no-record-biomass', action='store_true')
parser.add_argument('--no-stop-on-steady-state', action='store_true')
args = parser.parse_args()

kwargs = copy.copy(vars(args))
del kwargs['set_number']
del kwargs['timesteps']

simulation.simulate_batch(args.set_number, args.timesteps, **kwargs)
