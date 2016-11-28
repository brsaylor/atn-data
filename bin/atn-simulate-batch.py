#!/usr/bin/env python3

""" Runs a batch of simulations for a given set. """

import argparse

from atntools import simulation

parser = argparse.ArgumentParser(description=globals()['__doc__'])
parser.add_argument('set_number', type=int, help="Set number (set directory must exist under DATA_HOME)")
parser.add_argument('timesteps', type=int, help="Number of time steps to run the simulations")
args = parser.parse_args()

simulation.simulate_batch(args.set_number, args.timesteps)