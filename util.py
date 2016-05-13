#!/usr/bin/env python3

"""
Utility functions
"""

import os
import csv

WOB_DB_DIR = 'wob-database'

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

if __name__ == '__main__':
    pass
    #read_species_data_test()
