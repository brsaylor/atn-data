"""
Functions for running simulations
"""

import os
import subprocess
import re

from atntools import settings, util, nodeconfigs


def atn_engine_batch_runner(timesteps, node_config_file, use_webservices=False, use_csv=False, output_dir=None):
    """ Run ATNEngineBatchRunner from WoB Server with the given arguments. """

    node_config_file = os.path.abspath(os.path.expanduser(node_config_file))
    args = ['java', '-cp', 'build/libs/WoB_Server_ATNEngine.jar:lib/*:chartlib/*',
            'shared.atn.ATNEngineBatchRunner', str(timesteps), node_config_file]
    if use_webservices:
        args.append('--use-webservices')
    if use_csv:
        args.append('--use-csv')
    if output_dir:
        output_dir = os.path.abspath(os.path.expanduser(output_dir))
        args.extend(['--output-dir', output_dir])

    process = subprocess.Popen(args, cwd=settings.WOB_SERVER_HOME,
                               stdout=subprocess.PIPE, universal_newlines=True, bufsize=1)  # for reading stdout
    for line in process.stdout:
        match = re.match(r'Simulation (\d+)', line)
        if match:
            print("\rRunning simulation " + match.group(1), end='', flush=True)


def simulate_batch(set_num, timesteps):
    """ Run a batch of simulations for the given set.

    Parameters
    ----------
    set_num : int
        The set number
    timesteps
        Number of timesteps to run the simulations
    """
    set_dir = util.find_set_dir(set_num)
    if set_dir is None:
        raise RuntimeError("No directory found for set {}".format(set_num))

    batch_num, batch_dir = util.create_batch_dir(set_num)

    # Generate node config file
    metaparameter_file = os.path.join(set_dir, 'metaparameters.json')
    node_config_file = os.path.join(batch_dir, 'node-configs.txt')
    with open(node_config_file, 'w') as f:
        for node_config in nodeconfigs.generate_node_configs_from_metaparameter_file(metaparameter_file):
            print(node_config, file=f)

    output_dir = os.path.join(batch_dir, 'biomass-data')
    os.mkdir(output_dir)
    atn_engine_batch_runner(timesteps, node_config_file, output_dir=output_dir)
