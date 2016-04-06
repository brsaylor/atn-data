#!/usr/bin/env python3

import os
import csv
import random

import networkx as nx

from util import WOB_DB_DIR

def read_serengeti_from_csv():
    """
    Loads the Serengeti food web from CSV exports from the WoB database (the
    species and consume tables)
    """

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

    return g

def read_serengeti_from_graphml():
    return nx.readwrite.graphml.read_graphml('serengeti.graphml')

# According to %timeit in Jupyter
# read_serengeti_from_csv()
# is faster than
# read_serengeti_from_graphml()
read_serengeti = read_serengeti_from_csv

def random_subgraph(graph, N):
    """
    Return a subgraph of 'graph' containing N nodes selected at random and all
    of the edges between them. Not very useful for small food sub-webs, because
    the nodes are usually disconnected.
    """
    nodes = random.sample(graph.nodes(), N)
    return graph.subgraph(nodes)

if __name__ == '__main__':

    #nx.readwrite.graphml.write_graphml(g, 'serengeti.graphml')
    pass
