#!/usr/bin/env python3

"""
Loads the Serengeti food web from CSV exports from the WoB database (the species
and consume tables), and saves it in GraphML format.
"""

import os
import csv

import networkx as nx

WOB_DB_DIR = 'wob-database'

if __name__ == '__main__':
    
    g = nx.DiGraph()

    f = open(os.path.join(WOB_DB_DIR, 'species-table.csv'))
    reader = csv.DictReader(f)
    for row in reader:
        g.add_node(int(row['species_id']), **row)
    f.close()

    f = open(os.path.join(WOB_DB_DIR, 'consume-table.csv'))
    reader = csv.DictReader(f)
    for row in reader:
        g.add_edge(int(row['prey_id']), int(row['species_id']))
    f.close()

    nx.readwrite.graphml.write_graphml(g, 'serengeti.graphml')
