"""
Functions for running simulations
"""

import os
import subprocess

from atntools import settings


def atn_engine_batch_runner(timesteps, node_config_file, use_webservices=False, use_csv=False, output_dir=None):
    """ Run ATNEngineBatchRunner from WoB Server with the given arguments. """

    node_config_file = os.path.abspath(os.path.expanduser(node_config_file))
    args = ['java', '-cp', 'build/libs/WoB_Server_ATNEngine.jar:lib/*:chartlib/*',
               'atn.ATNEngineBatchRunner', str(timesteps), node_config_file]
    if use_webservices:
        args.append('--use-webservices')
    if use_csv:
        args.append('--use-csv')
    if output_dir:
        output_dir = os.path.abspath(os.path.expanduser(output_dir))
        args.extend(['--output-dir', output_dir])
    process = subprocess.run(args, cwd=settings.WOB_SERVER_HOME)
    process.check_returncode()
