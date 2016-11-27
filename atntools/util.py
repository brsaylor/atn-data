"""
Utility functions
"""

import os
import csv
import re
import collections
import json
import copy
import glob

from atntools import settings

WOB_DB_DIR = os.path.join(os.path.abspath(os.path.dirname(__file__)),
        'data/wob-database')


def typecast_dict_values(d, types):
    """
    Convert the values in the given dict to the given types,
    returning a new dict.
    """
    d2 = {}
    for k, v in d.items():
        if k in types:
            d2[k] = types[k](v)
        else:
            d2[k] = v
    return d2


_species_data = None


def get_species_data():
    """
    Returns species data from the WoB database export as read by
    read_species_csv(), but caches the result for later use.
    """
    global _species_data
    if _species_data is None:
        _species_data = read_species_csv()
    return _species_data


def read_species_csv():
    """
    Reads species-level data from the WoB database export and returns a dict of
    dicts. The main dict is indexed by species_id. For each species_id, the
    value is a dict of properties of that species, including a list of node IDs.
    """

    species_data = {}

    types = {
        'species_id': int,
        'organism_type': int,
        'cost': int,
        'biomass': float,
        'diet_type': int,
        'carrying_capacity': float,
        'metabolism': float,
        'trophic_level': float,
        'growth_rate': float,
        'model_id': int,
        'unlock': int,
        'node_id': int,
    }

    f = open(os.path.join(WOB_DB_DIR, 'species-table.csv'))
    reader = csv.DictReader(f)
    for row in reader:
        row = typecast_dict_values(row, types)
        species_id = row['species_id']
        if species_id in species_data:
            species_data[species_id]['node_id_list'].append(row['node_id'])
        else:
            row['node_id_list'] = [row['node_id']]
            del row['node_id']
            species_data[species_id] = row
    f.close()

    return species_data


def read_species_data_test():
    import json
    species_data = read_species_csv()
    print(json.dumps(species_data, sort_keys=True, indent=4))


def clip(x, xmin, xmax):
    """ Return the value of the first argument limited to the range given by the
    other two arguments. """
    return min(xmax, max(x, xmin))


def remove_trailing_digits(string):
    """ Return the string with trailing digits removed. """
    return re.match(r'(\D+)', string).group()


def get_food_web_dir(identifier):
    """ Get the food web directory path corresponding to the given identifier.

    This directory may or may not exist.

    Parameters
    ----------
    identifier : str or list of int
        A food web ID string or list of node IDs

    Returns
    -------
    str
        Food web directory path corresponding to `identifier`
    """
    if isinstance(identifier, str):
        food_web_id = identifier
        node_ids = food_web_id.split('-')
    elif isinstance(identifier, collections.Sequence):
        node_ids = sorted(identifier)
        food_web_id = '-'.join(map(str, node_ids))
    else:
        raise TypeError('{} is neither a food web ID nor a sequence of node IDs'.format(identifier))

    return os.path.join(settings.DATA_HOME, '{}-species'.format(len(node_ids)), food_web_id)


_set_dir_pattern = re.compile(r'set-(\d+)')


def list_set_dirs():
    """ List all set directories under DATA_HOME.

    Yields
    -------
    set_num : int, set_dir : str
        Each item yielded is a tuple containing the set number and
        the path to the set directory.
    """
    for root, dirs, files in os.walk(settings.DATA_HOME):
        remove_dirs = []
        for d in dirs:
            match = _set_dir_pattern.match(d)
            if match:
                remove_dirs.append(d)
                set_num = int(match.group(1))
                set_dir = os.path.join(root, d)
                yield set_num, set_dir
        (dirs.remove(d) for d in remove_dirs)


def list_batch_dirs(set_identifier):
    """ List all batch directories for the given set.

    Parameters
    ----------
    set_identifier : int or str
        Set number or set directory

    Yields
    -------
    batch_num : int, batch_dir : str
        Each item yielded is a tuple containing the batch number and
        the path to the batch directory.
    """
    if isinstance(set_identifier, int):
        set_dir = find_set_dir(set_identifier)
    else:
        set_dir = set_identifier

    for batch_dir in glob.iglob(os.path.join(set_dir, 'batch-*')):
        match = re.match(r'.+/batch-(\d+)', batch_dir)
        batch_num = int(match.group(1))
        yield batch_num, batch_dir


def find_set_dir(set_num):
    """ Find a set directory under DATA_HOME.

    Parameters
    ----------
    set_num : int
        Set number of the directory to find

    Returns
    -------
    str or None
        Path to the set directory, or None if it doesn't exist
    """
    for set_num_, set_dir in list_set_dirs():
        if set_num_ == set_num:
            return set_dir
    return None


def get_max_set_number():
    """ Find the maximum set number under DATA_HOME.

    Returns
    -------
    int
        The maximum set number
    """
    return max(set_num for set_num, set_dir in list_set_dirs())


def get_max_batch_number(set_identifier):
    """ Find the maximum batch number for the given set.

    Parameters
    ----------
    set_identifier : int or str
        Set number or set directory

    Returns
    -------
    int
        The maximum batch number, or None if no batch directories exist
    """
    batch_dirs = list(list_batch_dirs(set_identifier))
    if len(batch_dirs) == 0:
        return None
    else:
        return max(batch_num for batch_num, batch_dir in batch_dirs)


def create_set_dir(food_web, metaparameter_template):
    """ Create and initialize a new set directory for the given food web.

    Parameters
    ----------
    food_web : str or list of int
        A food web ID string or list of node IDs
    metaparameter_template : dict
        Metaparameter template to use. Node IDs are filled in from the
        food web info file.

    Returns
    -------
    set_num : int, set_dir : str
        A tuple containing the set number and the path to the set directory.
    """

    # Determine food web directory (assumed to exist) and set directory (does not exist)
    food_web_dir = get_food_web_dir(food_web)
    set_num = get_max_set_number() + 1
    set_dir = os.path.join(food_web_dir, 'set-{}'.format(set_num))

    # Create the set directory
    os.mkdir(set_dir)

    # Generate the metaparameter file from the template
    with open(os.path.join(food_web_dir, 'food-web.json')) as f:
        food_web_info = json.load(f)
    node_ids = food_web_info['node_ids']
    metaparameters = copy.copy(metaparameter_template)
    metaparameters['args']['node_ids'] = node_ids
    with open(os.path.join(set_dir, 'metaparameters.json'), 'w') as f:
        json.dump(metaparameters, f)

    return set_num, set_dir


def create_batch_dir(set_num):
    """ Create a batch directory for the given set.

    Parameters
    ----------
    set_num : int
        The set number

    Returns
    -------
    batch_num : int, batch_dir : str
        A tuple containing the batch number and the path to the newly
        created batch directory
    """

    set_dir = find_set_dir(set_num)
    max_batch_num = get_max_batch_number(set_num)
    if max_batch_num is None:
        batch_num = 0
    else:
        batch_num = max_batch_num + 1
    batch_dir = os.path.join(set_dir, 'batch-{}'.format(batch_num))
    os.mkdir(batch_dir)
    return batch_num, batch_dir
