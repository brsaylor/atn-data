"""
Automation for generating simulations for Convergence
"""

import os
import glob
import re
import logging
import copy
from collections import OrderedDict
import json

from atntools import settings, util, simulation

MAX_TIMESTEPS = 100000


def run_sequence(food_web, initial_metaparameter_template, cvg_metaparameter_template):

    sequence_num, sequence_dir = create_sequence_dir()

    log_filename = os.path.join(sequence_dir, 'log.txt')
    print("Logging to " + log_filename)
    logging.basicConfig(filename=log_filename, level=logging.INFO)
    logging.getLogger().addHandler(logging.StreamHandler())

    logging.info("Created sequence dir {}".format(sequence_dir))
    logging.info("Food web: {}".format(food_web))

    #
    # Initial set
    #

    initial_set, initial_set_dir = util.create_set_dir(food_web, initial_metaparameter_template)
    logging.info("Created initial set {}".format(initial_set))

    logging.info("Simulating initial batch, not saving biomass data")
    initial_batch = simulation.simulate_batch(
        initial_set, MAX_TIMESTEPS, no_record_biomass=True)
    print()

    #
    # Sustaining set
    #

    cvg_timesteps = cvg_metaparameter_template['args']['timesteps_to_analyze']

    sustaining_metaparameter_template = {
        'generator': 'filter-sustaining',
        'args': {
            'input_dir': os.path.join(
                util.find_batch_dir(initial_set_dir, initial_batch),
                'biomass-data')
        }
    }
    sustaining_set, sustaining_set_dir = util.create_set_dir(
        food_web, sustaining_metaparameter_template)
    logging.info("Created sustaining set {}".format(sustaining_set))

    logging.info("Simulating sustaining batch to steady state, saving biomass data")
    sustaining_batch = simulation.simulate_batch(sustaining_set, MAX_TIMESTEPS)
    print()

    #
    # Convergence set
    #

    cvg_metaparameter_template = copy.deepcopy(cvg_metaparameter_template)
    cvg_metaparameter_template['args']['input_set'] = sustaining_set
    cvg_metaparameter_template['args']['input_batch'] = sustaining_batch
    cvg_set, cvg_set_dir = util.create_set_dir(food_web, cvg_metaparameter_template)
    logging.info("Created convergence set {}".format(cvg_set))

    logging.info("Simulating convergence batch, saving {} timesteps of biomass data"
                 .format(cvg_timesteps))
    cvg_batch = simulation.simulate_batch(
        cvg_set, cvg_timesteps, no_stop_on_steady_state=True)
    print()

    sequence_info = OrderedDict([
        ('food_web', food_web),
        ('initial_set', initial_set),
        ('initial_batch', initial_batch),
        ('sustaining_set', sustaining_set),
        ('sustaining_batch', sustaining_batch),
        ('cvg_set', cvg_set),
        ('cvg_batch', cvg_batch),
    ])
    with open(os.path.join(sequence_dir, 'sequence-info.json'), 'w') as f:
        json.dump(sequence_info, f, indent=4)

    logging.info("Done.")


def create_sequence_dir():
    sequence_num = get_max_sequence_number() + 1
    sequence_dir = get_sequence_dir(sequence_num)
    os.makedirs(sequence_dir)
    return sequence_num, sequence_dir


def get_max_sequence_number():
    max_sequence_number = -1
    for sequence_dir in glob.iglob(os.path.join(settings.DATA_HOME, 'sequences/cvg-sequence-*')):
        match = re.match(r'.+?/cvg-sequence-(\d+)', sequence_dir)
        if match is None:
            continue
        sequence_num = int(match.group(1))
        if sequence_num > max_sequence_number:
            max_sequence_number = sequence_num
    return max_sequence_number


def get_sequence_dir(sequence_number):
    return os.path.join(settings.DATA_HOME, 'sequences/cvg-sequence-{}'.format(sequence_number))
