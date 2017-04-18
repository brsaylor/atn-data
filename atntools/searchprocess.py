import os
import glob
import re
import json
import csv
from collections import OrderedDict

import numpy as np
import pandas as pd
import pydotplus
from sklearn import tree
from sklearn.tree._tree import TREE_LEAF
from sklearn.tree import DecisionTreeClassifier
from sklearn.metrics import confusion_matrix, f1_score

from . import settings, util, simulation, summarize

TIMESTEPS = 100000
MIN_WEIGHT_FRACTION_LEAF = 0.01  # 1% of samples


def start_sequence(food_web, metaparameter_template):
    """ Create and initialize a new sequence directory for the given food web.

    Parameters
    ----------
    food_web : str or list of int
        A food web ID string or list of node IDs
    metaparameter_template : dict
        Metaparameter template to use. Node IDs are filled in from the
        food web info file.
    """

    sequence_num, sequence_dir = create_sequence_dir()

    set_num, set_dir = util.create_set_dir(food_web, metaparameter_template)
    sequence_state = {
        'sets': [set_num],
        'sequence_num': sequence_num
    }
    with open(os.path.join(sequence_dir, 'sequence-state.json'), 'w') as f:
        json.dump(sequence_state, f)

    with open(os.path.join(sequence_dir, 'log.txt'), 'a') as log:
        log.write("Initialized sequence {} with set {}\n".format(sequence_num, set_num))
        log.write("Food web: {}\n".format(food_web))
    print("Started sequence in {}".format(sequence_dir))


def do_iteration(sequence_num, no_record_biomass=True):

    sequence_dir = get_sequence_dir(sequence_num)
    state_filename = os.path.join(sequence_dir, 'sequence-state.json')

    with open(state_filename, 'r') as f:
        sequence_state = json.load(f)
    set_num = sequence_state['sets'][-1]
    set_dir = util.find_set_dir(set_num)
    iteration_num = len(sequence_state['sets']) - 1
    food_web_id = re.match(r'.*?((\d+-)+\d+).*', set_dir).group(1)
    
    log = open(os.path.join(sequence_dir, 'log.txt'), 'a')
    log.write("Starting iteration {}\n".format(iteration_num))
    log.write("Set {}\n".format(set_num))

    # Simulate and summarize the initial batch
    print("Simulating training batch")
    training_batch = simulation.simulate_batch(
        set_num, TIMESTEPS, no_record_biomass=no_record_biomass)
    summarize.generate_summary_file_for_batch(set_num, training_batch)
    log.write("Simulated training batch {}\n".format(training_batch))
    training_df = get_batch_summary(set_dir, training_batch)
    training_df, median_extinction_count = label_dataset(training_df)
    log.write("Extinction count frequencies:\n")
    log.write(str(training_df['extinction_count'].value_counts(normalize=True).sort_index()))
    log.write("\n")
    log.write("Class counts:\n")
    class_count_train = training_df['class_label'].value_counts()
    log.write(str(class_count_train))
    log.write("\n")

    # Prepare X_train
    X_cols = []
    for col in training_df.columns:
        if col[0] in ('K', 'X'):
            X_cols.append(col)
        elif col.startswith('initialBiomass'):
            X_cols.append(col)
    X_train = training_df[X_cols]

    # Prepare y_train
    y_train = training_df['class_label']

    # Fit the decision tree
    clf = DecisionTreeClassifier(
        min_samples_leaf=0.01,
        class_weight='balanced',
    )
    clf = clf.fit(X_train, y_train)

    # Evaluate it on the training data
    y_predict = clf.predict(X_train)
    log.write("Training confusion matrix:\n")
    log.write(str(confusion_matrix(y_train, y_predict)))
    log.write("\n")

    f1_train = f1_score(y_train, y_predict, average=None)
    log.write("Training f1-scores: {}\n".format(f1_train))

    #########

    print("Simulating test batch")
    test_batch = simulation.simulate_batch(
        set_num, TIMESTEPS, no_record_biomass=no_record_biomass)
    summarize.generate_summary_file_for_batch(set_num, test_batch)
    log.write("Simulated test batch {}\n".format(test_batch))
    test_df = get_batch_summary(set_dir, test_batch)
    test_df, _ = label_dataset(test_df, median_extinction_count)
    log.write("Extinction count frequencies:\n")
    log.write(str(test_df['extinction_count'].value_counts(normalize=True).sort_index()))
    log.write("\n")
    log.write("Class counts:\n")
    class_count_test = test_df['class_label'].value_counts()
    log.write(str(class_count_test))
    log.write("\n")

    # Evaluate tree on test data
    X_test = test_df[X_cols]
    y_test = test_df['class_label']
    y_predict = clf.predict(X_test)
    log.write("Training confusion matrix:\n")
    log.write(str(confusion_matrix(y_test, y_predict)))
    log.write("\n")
    f1_test = f1_score(y_test, y_predict, average=None)
    log.write("Test f1-scores: {}\n".format(f1_test))

    # Fold test data into training data and re-train the tree
    log.write("Combining train and test data\n")
    combined_df = training_df.append(test_df)
    X_combined = combined_df[X_cols]
    y_combined = combined_df['class_label']
    log.write("Extinction count frequencies:\n")
    extinction_freq = combined_df['extinction_count'].value_counts(normalize=True).sort_index()
    log.write(str(extinction_freq))
    log.write("\n")
    log.write("Class counts:\n")
    class_count_combined = combined_df['class_label'].value_counts()
    log.write(str(class_count_combined))
    log.write("\n")

    # Update extinction count frequency file
    node_ids = list(map(int, food_web_id.split('-')))
    node_count = len(node_ids)
    columns = range(node_count + 1)
    if iteration_num == 0:
        # First iteration: Make new dataframe
        extinction_freq_df = pd.DataFrame(columns=columns)
    else:
        # Subsequent iterations: Load file from previous iteration
        extinction_freq_df = pd.read_csv(
            os.path.join(sequence_dir, 'extinctions-iteration-{}.csv'.format(
                iteration_num - 1)),
            index_col=0)
        extinction_freq_df.columns = columns  # Workaround for pd not reading column labels as ints
    extinction_freq_df.loc[iteration_num] = extinction_freq
    extinction_freq_df.to_csv(
        os.path.join(sequence_dir, 'extinctions-iteration-{}.csv'.format(iteration_num)))

    clf = clf.fit(X_combined, y_combined)

    # Update sequence summary file
    iteration_data = OrderedDict([
        ('median_extinction_count', median_extinction_count),
        ('class_count_train_0', class_count_train[0]),
        ('class_count_train_1', class_count_train[1]),
        ('class_count_test_0', class_count_test[0]),
        ('class_count_test_1', class_count_test[1]),
        ('class_count_combined_0', class_count_combined[0]),
        ('class_count_combined_1', class_count_combined[1]),
        ('f1_train_0', f1_train[0]),
        ('f1_train_1', f1_train[1]),
        ('f1_test_0', f1_test[0]),
        ('f1_test_1', f1_test[1]),
        ('tree_node_count', clf.tree_.node_count),
    ])
    if iteration_num == 0:
        # First iteration: Make new dataframe
        sequence_df = pd.DataFrame(columns=list(iteration_data.keys()))
    else:
        # Subsequent iterations: Load file from previous iteration
        sequence_df = pd.read_csv(
            os.path.join(sequence_dir, 'iteration-{}.csv'.format(iteration_num - 1)),
            index_col=0,
            dtype=np.float64)
    sequence_df.loc[iteration_num] = iteration_data
    sequence_df.to_csv(os.path.join(sequence_dir, 'iteration-{}.csv'.format(iteration_num)))

    # Write final tree it to a PNG
    treefile = os.path.join(sequence_dir, 'tree-iteration-{}.png'.format(iteration_num))
    save_tree_image(clf, X_cols, treefile)

    #
    # Create the next set
    #

    # Get the metaparameters of the current set
    current_metaparameters = get_metaparameters_for_set(set_num)

    # Get the feature bounds of the root node from the current metaparameters
    root_bounds = get_root_bounds_from_metaparameters(X_cols, current_metaparameters)

    # Get the feature bounds of all nodes
    node_bounds = get_node_bounds(clf.tree_, root_bounds)

    # Get the feature bounds of the "good" leaves
    good_leaf_bounds = node_bounds[get_good_leaves(clf.tree_)]

    # Create the metaparameters for the next set
    next_metaparameters = make_multi_region_metaparameters(
        X_cols, good_leaf_bounds, current_metaparameters['args']['count'])

    # Create the next set!
    next_set_num, _ = util.create_set_dir(food_web_id, next_metaparameters)
    log.write("Created next set {}\n".format(next_set_num))

    # Update the state
    with open(state_filename, 'r') as f:
        sequence_state = json.load(f)
    sequence_state['sets'].append(next_set_num)
    with open(state_filename, 'w') as f:
        json.dump(sequence_state, f)

    log.close()


def create_sequence_dir():
    sequence_num = get_max_sequence_number() + 1
    sequence_dir = get_sequence_dir(sequence_num)
    os.makedirs(sequence_dir)
    return sequence_num, sequence_dir


def get_max_sequence_number():
    max_sequence_number = -1
    for sequence_dir in glob.iglob(os.path.join(settings.DATA_HOME, 'sequences/sequence-*')):
        match = re.match(r'.+?/sequence-(\d+)', sequence_dir)
        if match is None:
            continue
        sequence_num = int(match.group(1))
        if sequence_num > max_sequence_number:
            max_sequence_number = sequence_num
    return max_sequence_number


def get_sequence_dir(sequence_number):
    return os.path.join(settings.DATA_HOME, 'sequences/sequence-{}'.format(sequence_number))


def get_batch_summary(set_dir, batch_num):
    summary_file = os.path.join(util.find_batch_dir(set_dir, batch_num), 'summary.csv')
    return pd.read_csv(summary_file)


def label_dataset(df, median_extinction_count=None):
    """
    - filters out non-steady-state simulations
    - calculates median extinction count
    - assigns class labels based on medians
    """
    df = df[
        (df['stop_event'] != 'NONE') &
        (df['stop_event'] != 'UNKNOWN_EVENT')].copy()
    
    if median_extinction_count is None:
        median_extinction_count = df['extinction_count'].median()
    
    df['class_label'] = df['extinction_count'].map(lambda x: 1 if x < median_extinction_count else 0)
    
    return df, median_extinction_count


def save_tree_image(classifier, feature_names, outfile):
    dot_data = tree.export_graphviz(
        classifier, out_file=None,
        feature_names=feature_names,
        class_names=['bad', 'good'],
        filled=True, rounded=True, node_ids=True
    )
    graph = pydotplus.graph_from_dot_data(dot_data)
    graph.write_png(outfile)


def get_leaves(tree):
    """ Return the node IDs of the leaves in the given sklearn Tree """
    return [i for i in range(tree.node_count) if tree.children_left[i] == TREE_LEAF]


def get_good_leaves(tree):
    return [
        i for i in range(tree.node_count)
        if tree.children_left[i] == TREE_LEAF and tree.value[i, 0, 1] > tree.value[i, 0, 0]
    ]


def parse_feature_name(feature_name):
    """ Convert a feature name such as "X8" into a node-id, param-name pair such as (8, 'X') """
    match = re.match(r'^([a-zA-Z]+)(\d+)$', feature_name)
    if match is None:
        raise RuntimeError("Invalid feature name {}".format(feature_name))
    param = match.group(1)
    node_id = int(match.group(2))
    return node_id, param


def get_metaparameters_for_set(set_identifier):
    """ Parse the metaparameters.json file for the given set (directory or set number)
    and return the parsed dict.
    """
    if isinstance(set_identifier, int):
        set_dir = util.find_set_dir(set_identifier)
    else:
        set_dir = set_identifier

    with open(os.path.join(set_dir, 'metaparameters.json'), 'r') as f:
        metaparameters = json.load(f)
    
    return metaparameters


def get_root_bounds_from_uniform_metaparameters(feature_names, metaparameters):
    root_bounds = np.zeros((len(feature_names), 2))
    param_ranges = metaparameters['args']['param_ranges']
    for feature_id, feature_name in enumerate(feature_names):
        if feature_name.startswith('X'):
            bounds = param_ranges['X']
        elif feature_name.startswith('K'):
            bounds = param_ranges['K']
        elif feature_name.startswith('initialBiomass'):
            bounds = param_ranges['initialBiomass']
        else:
            raise RuntimeError("Unexpected feature name '{}'".format(feature_name))
        root_bounds[feature_id, :] = bounds
    
    return root_bounds


def get_root_bounds_from_multi_region_metaparameters(feature_names, metaparameters):
    """
    Outermost bounds for each feature (node-id, param pair)
    """
    root_bounds = np.empty((len(feature_names), 2))
    root_bounds[:, 0] = np.inf   # Smallest lower bound found so far for each feature
    root_bounds[:, 1] = -np.inf  # Largest upper bound found so far for each feature
    
    for feature_id, feature_name in enumerate(feature_names):
        node_id, param = parse_feature_name(feature_name)
        for region in metaparameters['args']['regions']:
            lower, upper = region['bounds'][str(node_id)][param]
            if lower < root_bounds[feature_id, 0]:
                root_bounds[feature_id, 0] = lower
            if upper > root_bounds[feature_id, 1]:
                root_bounds[feature_id, 1] = upper

    return root_bounds


def get_root_bounds_from_metaparameters(feature_names, metaparameters):
    generator = metaparameters['generator']
    if generator == 'uniform':
        return get_root_bounds_from_uniform_metaparameters(feature_names, metaparameters)
    elif generator == 'multi-region':
        return get_root_bounds_from_multi_region_metaparameters(feature_names, metaparameters)
    else:
        raise RuntimeError("Unexpected generator '{}' in metaparameters".format(generator))


def is_leaf(tree, node_id):
    return tree.children_left[node_id] == TREE_LEAF


def _calculate_node_bounds(tree, node_id, node_bounds):
    """
    Populate the node_bounds array rows for the children of node_id.
    
    Parameters
    ----------
    """
    
    if is_leaf(tree, node_id):
        return
    
    feature_id = tree.feature[node_id]
    feature_threshold = tree.threshold[node_id]
    
    # Calculate left child node bounds
    left_child_id = tree.children_left[node_id]
    node_bounds[left_child_id, :, :] = node_bounds[node_id, :, :]
    node_bounds[left_child_id, feature_id, 1] = min(feature_threshold, node_bounds[node_id, feature_id, 1])
    
    # Calculate right child node bounds
    right_child_id = tree.children_right[node_id]
    node_bounds[right_child_id, :, :] = node_bounds[node_id, :, :]
    node_bounds[right_child_id, feature_id, 0] = max(feature_threshold, node_bounds[node_id, feature_id, 0])
    
    # Traverse subtrees
    _calculate_node_bounds(tree, left_child_id, node_bounds)
    _calculate_node_bounds(tree, right_child_id, node_bounds)

    
def get_node_bounds(tree, root_bounds):
    node_bounds = np.zeros((tree.node_count, tree.n_features, 2))
    node_bounds[0, :, :] = root_bounds
    _calculate_node_bounds(tree, 0, node_bounds)
    return node_bounds


def features_to_node_param_pairs(feature_names):
    pairs = []
    for feature_name in feature_names:
        pairs.append(parse_feature_name(feature_name))
    return pairs


def make_region_list(feature_names, leaf_bounds):
    regions = []
    
    node_param_pairs = features_to_node_param_pairs(feature_names)
    node_ids = [p[0] for p in node_param_pairs]
    
    for bounds in leaf_bounds:
        region = {
            'weight': 1,
            'bounds': {i: {} for i in node_ids}
        }
        for feature_id, (lower, upper) in enumerate(bounds):
            node_id, param = node_param_pairs[feature_id]
            region['bounds'][node_id][param] = (lower, upper)
    
        regions.append(region)
        
    return regions


def make_multi_region_metaparameters(feature_names, leaf_bounds, count):
    return {
        'generator': 'multi-region',
        'args': {
            'count': count,
            'regions': make_region_list(feature_names, leaf_bounds)
        }
    }
