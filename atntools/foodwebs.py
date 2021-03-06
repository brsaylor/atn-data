#!/usr/bin/env python3
import json
import os
import csv
import random

import matplotlib
matplotlib.use('Agg')
from matplotlib.patches import Rectangle
import matplotlib.pyplot as plt
import networkx as nx

from atntools.util import WOB_DB_DIR

ORGANISM_TYPE_ANIMAL = 0
ORGANISM_TYPE_PLANT = 1


def read_serengeti_from_csv():
    """
    Loads the Serengeti food web from CSV exports from the WoB database (the
    species and consume tables, both of which have been INNER JOINED with
    species_nodes to include node IDs).
    """

    graph = nx.DiGraph()

    # Read the consume table (predator-prey relationships)
    # to create the nodes and edges of the graph
    f = open(os.path.join(WOB_DB_DIR, 'consume-table.csv'))
    reader = csv.DictReader(f)
    consume_species_ids = set()  # species IDs present in the consume table
    for row in reader:
        consume_species_ids.add(int(row['species_id']))
        consume_species_ids.add(int(row['prey_id']))
        prey_id = int(row['prey_node_id'])
        predator_id = int(row['predator_node_id'])
        assert not graph.has_edge(prey_id, predator_id)
        graph.add_edge(prey_id, predator_id)
    f.close()

    # Read the species table to add species attributes to the nodes
    f = open(os.path.join(WOB_DB_DIR, 'species-table.csv'))
    reader = csv.DictReader(f)
    for row in reader:
        species_id = int(row['species_id'])
        node_id = int(row['node_id'])
        if species_id in consume_species_ids:
            # Skip species that are not part of the food web
            # Add species attributes to node
            graph.node[node_id].update({
                'name': row['name'],
                'organism_type': int(row['organism_type']),
                'category': row['category'],
                'biomass': float(row['biomass']),
                'diet_type': int(row['diet_type']),
                'carrying_capacity': int(row['carrying_capacity']),
                'metabolism': float(row['metabolism']),
                'trophic_level': float(row['trophic_level']),
                'growth_rate': float(row['growth_rate']),
            })
    f.close()

    return graph


def read_serengeti():
    return read_serengeti_from_csv()


_serengeti = None


def get_serengeti():
    global _serengeti
    if _serengeti is None:
        _serengeti = read_serengeti_from_csv()
    return _serengeti


def draw_food_web(graph, show_names=False, show_legend=False, output_file=None, figsize=None, dpi=100):

    plt.figure(figsize=figsize)

    # pos = nx.spring_layout(graph)

    graphviz_prog = 'dot'
    # graphviz_prog = 'neato'
    pos = nx.drawing.nx_agraph.graphviz_layout(graph, prog=graphviz_prog, args='-Grankdir=BT')

    # Attempt at layout by trophic level. Doesn't work too well. Labels and edges overlap a lot.
    # pos = {}
    # count_by_trophic_level = {}
    # for node, data in graph.nodes_iter(data=True):
    #    trophic_level = float(data['trophic_level'])
    #    rounded_trophic_level = round(trophic_level)
    #    if rounded_trophic_level not in count_by_trophic_level:
    #        count_by_trophic_level[rounded_trophic_level] = 1
    #    else:
    #        count_by_trophic_level[rounded_trophic_level] += 1
    #    pos[node] = (count_by_trophic_level[rounded_trophic_level], trophic_level)
    # Using the positions calculated above as initial positions for spring_layout destroys the trophic-level-y
    # pos = nx.spring_layout(graph, pos=pos)

    # Instead, color nodes by trophic level.

    colors = [float(data['trophic_level']) * -1 + 5 for node, data in graph.nodes_iter(data=True)]

    # True vmin and vmax defining the color range are 1 and 4, but setting vmax to 4.5 to avoid the green getting too dark
    nx.draw_networkx_nodes(graph, pos, node_color=colors, cmap='RdYlGn', vmin=1, vmax=4.5)

    # nx.draw_networkx_nodes(graph, pos, node_size=colors)
    nx.draw_networkx_edges(graph, pos)

    plt.gca().set_axis_bgcolor('white')

    if show_names:
        labels = {node[0]: '  ' + str(node[0]) + ' ' + node[1]['name']
                  for node in graph.nodes(data=True)}

    else:
        labels = {node[0]: str(node[0])
                  for node in graph.nodes(data=True)}

    # Networkx can't draw self-loop edges, so add a ' C' to the label for cannibals
    for node in graph.nodes_with_selfloops():
        labels[node] = 'C{}  '.format(node)

    nx.draw_networkx_labels(graph, pos, labels)

    # Draw images
    # Not working yet; try http://stackoverflow.com/questions/4860417/placing-custom-images-in-a-plot-window-as-custom-data-markers-or-to-annotate-t
    # img = mpimg.imread('images/Aardvark.png')

    cur_axes = plt.gca()
    cur_axes.axes.get_xaxis().set_visible(False)
    cur_axes.axes.get_yaxis().set_visible(False)

    # plt.axis('off')

    if show_legend:
        invisible_handle = Rectangle((0, 0), 0, 0, alpha=0.0)
        lgd = plt.legend(
            [invisible_handle] * graph.number_of_nodes(),
            ['[{}] {}'.format(node_id, graph.node[node_id]['name'])
             for node_id in sorted(graph.nodes())],
            frameon=False,
            bbox_to_anchor=(0.9, 1), loc=2, borderaxespad=0.)

    if output_file:
        if show_legend:
            plt.savefig(output_file, bbox_extra_artists=(lgd,),
                        bbox_inches='tight', dpi=dpi)
        else:
            plt.savefig(output_file, dpi=dpi)
    #else:
    #    plt.show()
    return cur_axes


def random_subgraph(graph, N):
    """
    Return a subgraph of 'graph' containing N nodes selected at random and all
    of the edges between them. Not very useful for small food sub-webs, because
    the nodes are usually disconnected.
    """
    nodes = random.sample(graph.nodes(), N)
    return graph.subgraph(nodes)


def get_source_nodes(graph, allow_selfloops=True):
    """
    Get the source nodes (nodes with no in-edges) of the given graph.  If
    allow_selfloops is True, a node whose only in-edge is a self-loop is also
    considered a source node.
    """
    source_nodes = []
    for node, in_degree in graph.in_degree_iter():
        if in_degree == 0:
            source_nodes.append(node)
    if allow_selfloops:
        for node, in_degree in graph.in_degree_iter(graph.nodes_with_selfloops()):
            if in_degree == 1:
                source_nodes.append(node)
    return source_nodes


def all_simple_paths_from(graph, source, visited=set()):
    """ Compute all simple paths in the given directed graph from the given source node.

    Parameters
    ----------
    graph : nx.DiGraph
        The graph to search
    source : int
        The source node
    visited : set of int, optional
        The set of nodes that have been visited so far

    Returns
    -------
    list of list of int
        The simple paths from `source`
    """
    paths = []
    for successor in graph.successors(source):
        if successor not in visited and successor != source:
            paths.append([source, successor])
            for successor_path in all_simple_paths_from(graph, successor, visited | set([source])):
                paths.append([source] + successor_path)
    return paths


def get_food_chains(graph):
    """ Get all food chains in the graph.

    A food chain is defined here as a simple path from a source node
    (a node with no predecessors) to another node.

    Parameters
    ----------
    graph : nx.DiGraph
        The graph to search for food chains

    Returns
    -------
    list of list of int
        All food chains in the graph as a list of simple paths
    """
    food_chains = []
    for source in get_source_nodes(graph):
        food_chains += all_simple_paths_from(graph, source)
    return food_chains


def get_basal_species(graph):
    basal_species = []
    for node_id, species_attributes in graph.nodes_iter(data=True):
        if float(species_attributes['trophic_level']) == 1:
            basal_species.append(node_id)
    return basal_species


def get_plant_eaters(graph):
    """
    Return the set of nodes which have a source node as a predecessor.
    """
    plant_eaters = set()
    for plant in get_source_nodes(graph):
        for node in graph.successors(plant):
            plant_eaters.add(node)
    return plant_eaters


# This is a hack
_predator_complete_subweb_retry_count = 0

def predator_complete_subweb(G, N, seed_nodes=None, seed_size=1, retry=1):
    """
    A version of random_successor_subgraph with the following addition: Each
    iteration, before choosing a random neighbor, choose a neighbor of a plant
    eater which does not currently have a predator ("lonely plant eater") in the
    subgraph (if any).
    
    The goal is to produce a sub-web in which everything that eats plants has a
    predator, but this is not guaranteed, because:
    - Some plant eaters have no predators in the full graph
      (e.g. African Elephant, Hippopotamus)
    - N might be too small to ensure all plant eaters have predators 
    
    seed_nodes: list of nodes from which to randomly choose seed_size starting
    nodes
    """
    global _predator_complete_subweb_retry_count

    if seed_nodes is None:
        seed_nodes = G.nodes()
    nodes = set(random.sample(seed_nodes, seed_size))

    plant_eaters = get_plant_eaters(G)

    for i in range(N - seed_size):

        # Identify any plant eaters without predators
        lonely_plant_eaters = {}  # key: plant eater node; value: list of predator nodes
        # For each plant eater in the current subgraph
        for node in plant_eaters & nodes:
            predators = G.successors(node)
            if node in predators:
                predators.remove(node)  # don't count self as predator (cannibals)
            if len(predators) == 0:
                pass
                # print("Lonely plant eater {} has no predators in full graph".format(node))
            # If the current subgraph does not contain any of the plant eater's successors
            elif len(nodes & set(predators)) == 0:
                lonely_plant_eaters[node] = predators

        # If there are any lonely plant eaters, add a random predator of of any of them
        # and skip to the next iteration of the loop.
        if len(lonely_plant_eaters) > 0:
            candidate_predators = []
            for node, predators in lonely_plant_eaters.items():
                candidate_predators.extend(predators)
            if len(candidate_predators) > 0:
                nodes.add(random.choice(candidate_predators))
                continue

        # Find the neighbor nodes of the subgraph nodes
        neighbors = set()
        for node in nodes:
            neighbors = neighbors | set(G.successors(node))
        neighbors = neighbors - nodes  # Exclude nodes already in the subgraph

        if len(neighbors) == 0:
            #print("predator_complete_subweb: no candidate neighbors found. ", end='')
            if (retry > 0):
                #print("Retrying.")
                _predator_complete_subweb_retry_count += 1
                return predator_complete_subweb(G, N, seed_nodes, seed_size=seed_size,
                                                retry=retry - 1)
            else:
                #print("Giving up.")
                return None

        # Add a random neighbor to the subgraph
        nodes.add(random.choice(list(neighbors)))

    subgraph = G.subgraph(list(nodes))
    num_components = nx.number_connected_components(subgraph.to_undirected())
    if num_components > 1:
        #print("random_successor_subgraph: {} connected components. ".format(num_components),
        #     end='')
        if (retry > 0):
        #   print("Retrying.")
            _predator_complete_subweb_retry_count += 1
            return predator_complete_subweb(G, N, seed_nodes, seed_size=seed_size,
                                            retry=retry - 1)
        else:
        #   print("Giving up.")
            return None

    return subgraph


def serengeti_predator_complete_subweb(size, num_basal_species, retry=10):
    serengeti = get_serengeti()

    # For the seed nodes, use the basal species excluding Decaying Material
    seed_nodes = get_basal_species(serengeti)
    if 1 in seed_nodes:
        seed_nodes.remove(1)

    return predator_complete_subweb(serengeti, size, seed_nodes=seed_nodes,
                                    seed_size=num_basal_species, retry=retry)


def species_node_id_map(graph):
    """ Build a map of species IDs to node IDs.

    Parameters
    ----------
    graph : networkx.DiGraph
        The Serengeti food web

    Returns
    -------
    dict
        Dictionary mapping species ID to node ID
    """
    id_map = {}
    for node_id, data in graph.nodes(data=True):
        species_id = int(data['species_id'])
        assert species_id not in id_map
        id_map[species_id] = node_id
    return id_map


def connected_components(graph):
    """ Return a list of the separate connected components of `graph`.
    Each component in the list is a frozenset of node IDs.
    """
    return list(map(frozenset, nx.connected_components(graph.to_undirected())))
    

def food_web_json(graph):
    """ Generate a JSON representation of the given food web.

    Parameters
    ----------
    graph : networkx.DiGraph
        The food web

    Returns
    -------
    str
        JSON representation of the food web
    """

    node_attributes = {}
    links = {}
    for node_id, data in graph.nodes(data=True):
        if data['organism_type'] == ORGANISM_TYPE_PLANT:
            node_type = 'PRODUCER'
        else:
            node_type = 'CONSUMER'
        node_attributes[node_id] = {'nodeType': node_type}
        links[node_id] = graph.successors(node_id)

    food_web_dict = {'nodeAttributes': node_attributes, 'links': links}

    return json.dumps(food_web_dict, indent=4, sort_keys=True)
