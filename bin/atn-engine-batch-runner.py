#!/usr/bin/env python3

""" Executes ATNEngineBatchRunner from WoB Server to run a batch of simulations. """

import argparse

from atntools.simulation import atn_engine_batch_runner


parser = argparse.ArgumentParser(description=globals()['__doc__'])
parser.add_argument('timesteps', type=int,
                    help="Number of timesteps to run all simulations")
parser.add_argument('node_config_file',
                    help="File containing node config strings, one per line")
parser.add_argument('--use-webservices', action='store_true',
                    help="Use Web Services to run the simulation, rather than running locally")
parser.add_argument('--use-csv', action='store_true',
                    help="Save output data in CSV format instead of HDF5 format")
parser.add_argument('--output-dir', help="Output directory (default: $WOB_SERVER_HOME/src/log/(atn|sim)")
parser.add_argument('--threads', type=int, help="Number of simulation threads to run (default: 1)")
args = parser.parse_args()

atn_engine_batch_runner(**vars(args))
